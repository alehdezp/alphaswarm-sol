# VERIFICATION-2.1-02: Emitted Properties Usage Verification

**Date:** 2026-02-08
**Status:** COMPLETE
**Confidence:** HIGH (automated grep across 668 YAML files + all Python source)

## Summary

275 unique properties are emitted in `_compute_function_properties()` (lines 1065-1361 of `functions.py`).
Of these, **222 (80.7%)** are referenced by at least one YAML pattern file.
**53 (19.3%)** have zero YAML references, but **27 of those 53** are consumed by Python code (query engine, semantic layer, classification, evidence system). Only **26 properties (9.5%)** are truly dead -- referenced nowhere except in builder files where they are defined.

---

## 1. Property Reference Counts (All 275 Properties)

### Top-Referenced Properties (>20 YAML files)

| Property | YAML Refs |
|----------|-----------|
| `visibility` | 152 |
| `signature` | 120 |
| `has_access_gate` | 90 |
| `behavioral_signature` | 88 |
| `writes_state` | 59 |
| `semantic_ops` | 53 |
| `has_reentrancy_guard` | 44 |
| `state_write_after_external_call` | 37 |
| `has_external_calls` | 31 |
| `is_constructor` | 28 |
| `modifiers` | 28 |
| `is_initializer_function` | 26 |
| `is_view` | 25 |
| `payable` | 25 |
| `writes_privileged_state` | 24 |
| `mutability` | 23 |
| `reads_oracle_price` | 23 |
| `uses_ecrecover` | 23 |
| `is_pure` | 21 |
| `state_mutability` | 21 |

### Mid-Referenced Properties (6-20 YAML files)

| Property | YAML Refs |
|----------|-----------|
| `has_staleness_check` | 17 |
| `writes_sensitive_config` | 16 |
| `has_require_bounds` | 15 |
| `has_timelock` | 15 |
| `has_multi_source_oracle` | 14 |
| `has_multisig` | 14 |
| `uses_call` | 14 |
| `uses_delegatecall` | 14 |
| `call_target_user_controlled` | 12 |
| `has_loops` | 12 |
| `is_upgradeable` | 12 |
| `uses_erc20_transfer` | 12 |
| `contract_has_multisig` | 11 |
| `file` | 11 |
| `has_sequencer_uptime_check` | 11 |
| `is_upgrade_function` | 11 |
| `checks_low_level_call_success` | 10 |
| `has_unbounded_loop` | 10 |
| `reads_twap` | 10 |
| `risk_missing_slippage_parameter` | 10 |
| `uses_erc20_transfer_from` | 10 |
| `has_deadline_check` | 9 |
| `has_deadline_parameter` | 9 |
| `has_initializer_modifier` | 9 |
| `token_return_guarded` | 9 |
| `external_calls_in_loop` | 8 |
| `flash_loan_guard` | 8 |
| `has_access_control` | 8 |
| `writes_nonce_state` | 8 |
| `access_gate_sources` | 7 |
| `checks_initialized_flag` | 7 |
| `has_access_modifier` | 7 |
| `has_array_parameter` | 7 |
| `has_nonce_parameter` | 7 |
| `is_deposit_like` | 7 |
| `is_withdraw_like` | 7 |
| `state_write_targets` | 7 |
| `swap_like` | 7 |
| `uses_erc20_approve` | 7 |
| `uses_tx_origin` | 7 |
| `callback_chain_surface` | 6 |
| `calls_chainlink_latest_round_data` | 6 |
| `contract_is_upgradeable` | 6 |
| `has_arithmetic` | 6 |
| `has_division` | 6 |
| `has_try_catch` | 6 |
| `is_fallback` | 6 |
| `is_receive` | 6 |
| `loop_bound_sources` | 6 |
| `risk_missing_deadline_check` | 6 |
| `risk_missing_deadline_parameter` | 6 |
| `risk_missing_slippage_check` | 6 |

### Low-Referenced Properties (2-5 YAML files)

| Property | YAML Refs |
|----------|-----------|
| `checks_received_amount` | 5 |
| `checks_zero_address` | 5 |
| `contract_has_timelock` | 5 |
| `delegatecall_target_user_controlled` | 5 |
| `has_call_with_value` | 5 |
| `has_precision_guard` | 5 |
| `has_timelock_check` | 5 |
| `is_implementation_contract` | 5 |
| `is_privileged_operation` | 5 |
| `uses_chainid` | 5 |
| `uses_domain_separator` | 5 |
| `uses_safe_erc20` | 5 |
| `uses_safemath` | 5 |
| `call_target_validated` | 4 |
| `contract_is_uups_proxy` | 4 |
| `has_low_level_calls` | 4 |
| `has_privileged_operations` | 4 |
| `has_twap_validation` | 4 |
| `has_twap_window_parameter` | 4 |
| `is_burn_like` | 4 |
| `is_callback` | 4 |
| `is_mint_like` | 4 |
| `is_permit_like` | 4 |
| `low_level_calls` | 4 |
| `reads_balance_state` | 4 |
| `reads_share_state` | 4 |
| `time_based_access_control` | 4 |
| `transfers_eth` | 4 |
| `uses_allowance_adjust` | 4 |
| `uses_division` | 4 |
| `writes_balance_state` | 4 |
| `writes_supply_state` | 4 |
| `calls_external_contract` | 3 |
| `contract_has_balance_tracking` | 3 |
| `contract_has_composition` | 3 |
| `contract_has_inheritance` | 3 |
| `contract_has_withdraw` | 3 |
| `flash_loan_sensitive_operation` | 3 |
| `has_amount_parameter` | 3 |
| `has_balance_check` | 3 |
| `has_pause_check` | 3 |
| `has_strict_equality_check` | 3 |
| `has_unbounded_deletion` | 3 |
| `has_untrusted_external_call` | 3 |
| `has_user_input` | 3 |
| `is_emergency_function` | 3 |
| `reads_nonce_state` | 3 |
| `reads_pool_reserves` | 3 |
| `uses_balance_of` | 3 |
| `uses_block_timestamp` | 3 |
| `validates_delegatecall_target` | 3 |
| `accepts_address_parameter` | 2 |
| `call_data_user_controlled` | 2 |
| `call_value_user_controlled` | 2 |
| `callback_entrypoint_surface` | 2 |
| `calls_chainlink_decimals` | 2 |
| `checks_returndata_length` | 2 |
| `checks_token_call_return` | 2 |
| `compiler_version_lt_08` | 2 |
| `contract_is_beacon_proxy` | 2 |
| `decodes_call_return` | 2 |
| `event_emission_in_loop` | 2 |
| `flash_loan_callback` | 2 |
| `flash_loan_validation` | 2 |
| `has_bytes_parameter` | 2 |
| `has_deadline_future_check` | 2 |
| `has_delete_in_loop` | 2 |
| `has_duration_bounds` | 2 |
| `has_duration_parameter` | 2 |
| `has_governance` | 2 |
| `has_hardcoded_gas` | 2 |
| `has_only_proxy_modifier` | 2 |
| `has_pagination_parameter` | 2 |
| `has_require_msg_sender` | 2 |
| `has_slippage_parameter` | 2 |
| `has_timelock_parameter` | 2 |
| `has_unchecked_block` | 2 |
| `is_timelock_admin_function` | 2 |
| `is_value_transfer` | 2 |
| `semgrep_like_rules` | 2 |
| `timestamp_arithmetic` | 2 |
| `token_call_kinds` | 2 |
| `token_callback_surface` | 2 |
| `unchecked_affects_balance` | 2 |
| `unchecked_contains_arithmetic` | 2 |
| `unchecked_operand_from_user` | 2 |
| `uses_erc777_send` | 2 |
| `uses_transfer` | 2 |
| `validates_answer_positive` | 2 |
| `validates_answered_in_round_matches_round_id` | 2 |
| `validates_updated_at_recent` | 2 |

### Single-Reference Properties (1 YAML file)

| Property | YAML Refs |
|----------|-----------|
| `approves_infinite_amount` | 1 |
| `contract_has_beacon_state` | 1 |
| `contract_has_emergency_withdraw` | 1 |
| `contract_has_governance` | 1 |
| `contract_is_implementation_contract` | 1 |
| `decimal_scaling_usage` | 1 |
| `division_before_multiplication` | 1 |
| `divisor_source` | 1 |
| `divisor_validated_nonzero` | 1 |
| `external_call_count` | 1 |
| `fee_accumulation` | 1 |
| `handles_oracle_revert` | 1 |
| `has_bytes_length_check` | 1 |
| `has_bytes_or_string_parameter` | 1 |
| `has_call_with_gas` | 1 |
| `has_deadline_max` | 1 |
| `has_deadline_min_buffer` | 1 |
| `has_fee_bounds` | 1 |
| `has_fee_parameter` | 1 |
| `has_internal_calls` | 1 |
| `has_minimum_output` | 1 |
| `has_multiplication` | 1 |
| `has_nested_loop` | 1 |
| `has_only_owner` | 1 |
| `has_only_role` | 1 |
| `has_rounding_ops` | 1 |
| `has_sequencer_grace_period` | 1 |
| `has_slippage_check` | 1 |
| `has_staleness_threshold` | 1 |
| `has_threshold_parameter` | 1 |
| `is_admin_named` | 1 |
| `large_number_multiplication` | 1 |
| `loop_count` | 1 |
| `low_level_call_count` | 1 |
| `mapping_iteration_in_loop` | 1 |
| `parameter_types` | 1 |
| `performs_swap` | 1 |
| `public_wrapper_without_access_gate` | 1 |
| `ratio_calculation` | 1 |
| `reads_dex_reserves` | 1 |
| `reads_state` | 1 |
| `tx_origin_in_require` | 1 |
| `uses_arithmetic` | 1 |
| `uses_erc1155_mint` | 1 |
| `uses_erc1155_mint_batch` | 1 |
| `uses_erc1155_safe_batch_transfer` | 1 |
| `uses_erc1155_safe_transfer` | 1 |
| `uses_erc4626_deposit` | 1 |
| `uses_erc4626_mint` | 1 |
| `uses_erc4626_redeem` | 1 |
| `uses_erc4626_withdraw` | 1 |
| `uses_erc721_safe_mint` | 1 |
| `uses_erc721_safe_transfer` | 1 |
| `uses_erc777_operator_send` | 1 |
| `uses_msg_sender` | 1 |
| `uses_msg_value` | 1 |
| `uses_send` | 1 |
| `uses_unchecked_block` | 1 |
| `validates_started_at_recent` | 1 |

---

## 2. Zero-YAML-Reference Properties (53 total)

### 2a. Truly Dead Properties (26) -- Builder-only, no YAML, no Python consumer

These properties are computed and emitted by the builder but consumed by **nothing** downstream.

| # | Property | Category |
|---|----------|----------|
| 1 | `access_control_uses_or` | Access Control |
| 2 | `auth_patterns` | Access Control |
| 3 | `contract_has_emergency_pause` | Contract Context |
| 4 | `flash_loan_asset_checked` | Flash Loan |
| 5 | `flash_loan_initiator_checked` | Flash Loan |
| 6 | `flash_loan_repayment_checked` | Flash Loan |
| 7 | `has_v3_struct_params` | Swap/DEX |
| 8 | `internal_call_count` | Call Metrics |
| 9 | `is_liquidation_like` | Function Classification |
| 10 | `is_multicall_function` | Function Classification |
| 11 | `is_reward_like` | Function Classification |
| 12 | `max_loop_depth` | Loop Analysis |
| 13 | `oracle_call_count` | Oracle |
| 14 | `oracle_source_count` | Oracle |
| 15 | `oracle_source_targets` | Oracle |
| 16 | `parameter_names` | Parameter Info |
| 17 | `protocol_callback_chain_surface` | Reentrancy |
| 18 | `reads_state_count` | State Metrics |
| 19 | `reads_supply_state` | State Tracking |
| 20 | `semgrep_like_count` | Semgrep |
| 21 | `semgrep_like_security_count` | Semgrep |
| 22 | `state_read_targets` | State Tracking |
| 23 | `uses_erc777_burn` | Token Ops |
| 24 | `uses_erc777_mint` | Token Ops |
| 25 | `uses_total_supply` | Token Ops |
| 26 | `writes_state_count` | State Metrics |

### 2b. Zero-YAML but Python-Consumed (27) -- Not dead, used programmatically

These have no YAML pattern references but are consumed by VQL2 semantic engine, property_sets, classification, evidence system, etc.

| # | Property | Consumers |
|---|----------|-----------|
| 1 | `access_gate_logic` | semantic.py, property_sets.py |
| 2 | `access_gate_modifiers` | property_sets.py |
| 3 | `basis_points_calculation` | semantic.py |
| 4 | `contract_is_diamond_proxy` | semantic.py |
| 5 | `fee_calculation` | semantic.py |
| 6 | `has_auth_pattern` | semantic.py |
| 7 | `has_minimum_output_parameter` | semantic.py |
| 8 | `input_count` | tools.py, dedup.py |
| 9 | `line_end` | 14+ files (evidence, subagents, schema, etc.) |
| 10 | `line_start` | 17+ files (evidence, subagents, schema, etc.) |
| 11 | `op_ordering` | patterns.py, creative.py |
| 12 | `op_sequence` | fingerprint.py |
| 13 | `oracle_freshness_ok` | semantic.py, property_sets.py |
| 14 | `oracle_round_check` | property_sets.py |
| 15 | `percentage_bounds_check` | semantic.py |
| 16 | `percentage_calculation` | semantic.py |
| 17 | `price_amount_multiplication` | semantic.py |
| 18 | `reads_twap_with_window` | semgrep_compat.py |
| 19 | `state_write_before_external_call` | semantic.py, classification.py, property_sets.py |
| 20 | `uses_block_hash` | intent.py, semantic.py, semgrep_compat.py |
| 21 | `uses_block_number` | intent.py, semantic.py |
| 22 | `uses_block_prevrandao` | intent.py, semantic.py |
| 23 | `uses_erc20_burn` | semgrep_compat.py, property_sets.py |
| 24 | `uses_erc20_mint` | property_sets.py |
| 25 | `uses_muldiv_or_safemath` | semantic.py |
| 26 | `uses_token_decimals` | semantic.py |
| 27 | `writes_share_state` | semantic.py |

---

## 3. Missing Cross-Function Reentrancy Properties

### Status: NOT missing from the graph -- set via post-processing

The two properties `cross_function_reentrancy_surface` and `cross_function_reentrancy_read`:

- **Defined in dataclass** (`FunctionProperties`, lines 297-298)
- **NOT in the `_compute_function_properties()` props dict** (lines 1065-1361)
- **Set via post-processing** in `builder/core.py` lines 594-599 and `builder.py` lines 1953-1977

The post-processing logic in `_compute_cross_function_reentrancy()`:
1. Collects all Function nodes
2. Finds readers (`reads_balance_state=True`) and writers (`writes_balance_state=True`)
3. When different functions read and write balance state, marks both:
   - Reader: `cross_function_reentrancy_read = True`
   - Writer: `cross_function_reentrancy_surface = True`

**Verification on ArithmeticLens.sol**: `uncheckedAdd` correctly shows both `cross_function_reentrancy_surface: True` and `cross_function_reentrancy_read: True` (it both reads and writes `balance` state).

**YAML references**: 7 YAML files reference these properties, including:
- `vulndocs/reentrancy/cross-function/patterns/cross-function-reentrancy.yaml`
- `vulndocs/reentrancy/classic/patterns/value-movement-cross-function-reentrancy.yaml`
- `vulndocs/reentrancy/classic/patterns/value-movement-cross-function-reentrancy-read.yaml`
- `vulndocs/reentrancy/general/patterns/vm-003.yaml`
- `vulndocs/reentrancy/general/patterns/vm-013.yaml`
- `vulndocs/.meta/references/lens/value-movement-lens.yaml` (2 references)

**Conclusion**: These are NOT dead. They are correctly computed but via a different code path (post-processing rather than initial props dict). This is intentional -- cross-function analysis requires seeing all functions before it can reason about pairs.

---

## 4. Property Values on Real Contracts (Correctness Check)

### NoAccessGate.sol -- `setOwner(address)`

| Property | Value | Correct? |
|----------|-------|----------|
| `visibility` | `external` | YES |
| `has_access_gate` | `False` | YES (known vulnerable: no access control) |
| `writes_state` | `True` | YES (writes `owner`) |
| `is_privileged_operation` | `True` | YES (modifies owner) |
| `behavioral_signature` | `M:crit->M:own` | YES |

### AuthReentrancyNoGuard.sol -- `emergencyCall(address,bytes)`

| Property | Value | Correct? |
|----------|-------|----------|
| `has_access_gate` | `True` | YES (has `require(msg.sender == owner)`) |
| `has_external_calls` | `True` | YES (uses `.call()`) |
| `call_target_user_controlled` | `True` | YES (target from parameter) |
| `call_data_user_controlled` | `True` | YES (data from parameter) |
| `is_emergency_function` | `True` | YES (name matches) |
| `has_reentrancy_guard` | `False` | YES (known missing) |

### ArithmeticLens.sol -- `uncheckedAdd(uint256)`

| Property | Value | Correct? |
|----------|-------|----------|
| `has_arithmetic` | `True` | YES |
| `has_unchecked_block` | `True` | YES |
| `unchecked_contains_arithmetic` | `True` | YES |
| `unchecked_operand_from_user` | `True` | YES (amount is parameter) |
| `unchecked_affects_balance` | `True` | YES (writes balance mapping) |
| `reads_balance_state` | `True` | YES |
| `writes_balance_state` | `True` | YES |
| `cross_function_reentrancy_surface` | `True` | YES (via post-processing) |

All sampled property values are correct.

---

## 5. Summary

### Distribution of 275 Emitted Properties

| Category | Count | Percentage |
|----------|-------|------------|
| Referenced by >20 YAML files | 20 | 7.3% |
| Referenced by 6-20 YAML files | 52 | 18.9% |
| Referenced by 2-5 YAML files | 91 | 33.1% |
| Referenced by 1 YAML file | 59 | 21.5% |
| Zero YAML but Python-consumed | 27 | 9.8% |
| **Truly dead (no consumer)** | **26** | **9.5%** |

### Key Findings

1. **80.7% of emitted properties** have at least one YAML pattern reference. The property-to-pattern pipeline is well connected.

2. **9.8% (27 properties)** have no YAML references but are consumed by Python code (VQL2 semantic engine, property sets, classification, evidence system). These are not dead -- they serve the programmatic query and analysis layers.

3. **9.5% (26 properties)** are truly dead code -- emitted but consumed by nothing downstream. These fall into categories:
   - **Flash loan details** (3): `flash_loan_asset_checked`, `flash_loan_initiator_checked`, `flash_loan_repayment_checked` -- fine-grained checks with no patterns written yet
   - **Function classification** (3): `is_liquidation_like`, `is_multicall_function`, `is_reward_like` -- useful semantic classifiers waiting for patterns
   - **Oracle details** (3): `oracle_call_count`, `oracle_source_count`, `oracle_source_targets` -- quantitative oracle data unused
   - **State metrics** (4): `internal_call_count`, `reads_state_count`, `writes_state_count`, `reads_supply_state` -- raw counts not needed by patterns
   - **Misc** (13): various unused properties

4. **Cross-function reentrancy properties** are NOT missing from the graph. They are correctly computed via post-processing in `builder/core.py` after all functions are analyzed, and referenced by 7+ YAML files.

5. **Property values are correct** on real contracts (verified on 3 contracts with known vulnerability characteristics).

### Recommendation

- The 26 truly dead properties are **low-priority waste** (each is a single dict key-value assignment, negligible performance impact).
- Consider writing patterns for high-value dead properties: `flash_loan_initiator_checked`, `is_liquidation_like`, `is_multicall_function`, `reads_supply_state`.
- The 59 single-reference properties are fragile -- a single pattern removal makes them dead. Consider expanding coverage.
- **Overall health: GOOD.** 90.5% of emitted properties are consumed somewhere downstream.
