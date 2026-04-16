"""Function processing for VKG builder.

This module extracts and structures function analysis from the legacy builder,
organizing the massive _add_functions method (~1400 LOC) into logical groups.

The FunctionProcessor computes 50+ security properties for each function node.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from alphaswarm_sol.kg.schema import Node, Edge, Evidence
from alphaswarm_sol.kg.heuristics import classify_state_var_name, is_privileged_state
from alphaswarm_sol.kg.operations import derive_all_operations, compute_behavioral_signature, compute_ordering_pairs
from alphaswarm_sol.kg.taint import compute_dataflow, extract_inputs, extract_special_sources
from alphaswarm_sol.kg.semgrep_compat import FunctionContext, SECURITY_RULES, detect_semgrep_function_rules

from alphaswarm_sol.kg.builder.helpers import (
    source_location,
    relpath,
    evidence_from_location,
    function_label,
    is_access_gate,
    uses_var_name,
    strip_comments,
    node_expression,
    callsite_data_expression,
    callsite_destination,
    node_id_hash,
    edge_id_hash,
    is_user_controlled_destination,
    is_user_controlled_expression,
    is_hardcoded_gas,
    normalize_state_mutability,
    classify_parameter_types,
    node_type_name,
    is_loop_start,
    is_loop_end,
    node_has_external_call,
    node_has_delete,
    get_source_slice,
)

if TYPE_CHECKING:
    from alphaswarm_sol.kg.builder.context import BuildContext
    from alphaswarm_sol.kg.schema import KnowledgeGraph


@dataclass
class FunctionProperties:
    """All computed properties for a function node.

    This dataclass holds the 50+ security properties computed
    during function analysis, organized into logical groups.
    """

    # =========================================================================
    # 1. Basic Identity & Visibility (8 properties)
    # =========================================================================
    visibility: str
    state_mutability: str
    is_constructor: bool = False
    is_fallback: bool = False
    is_receive: bool = False
    is_view: bool = False
    payable: bool = False
    signature: str | None = None

    # =========================================================================
    # 2. Access Control (18 properties)
    # =========================================================================
    modifiers: list[str] = field(default_factory=list)
    has_access_gate: bool = False
    has_access_control: bool = False
    has_access_modifier: bool = False
    access_gate_modifiers: list[str] = field(default_factory=list)
    access_gate_logic: bool = False
    access_gate_sources: list[str] = field(default_factory=list)
    access_control_uses_or: bool = False
    has_only_owner: bool = False
    has_only_role: bool = False
    has_reentrancy_guard: bool = False
    has_initializer_modifier: bool = False
    has_only_proxy_modifier: bool = False
    checks_initialized_flag: bool = False
    time_based_access_control: bool = False
    has_require_msg_sender: bool = False
    auth_patterns: list[str] = field(default_factory=list)
    has_auth_pattern: bool = False

    # =========================================================================
    # 3. State Operations (14 properties)
    # =========================================================================
    reads_state: bool = False
    writes_state: bool = False
    reads_state_count: int = 0
    writes_state_count: int = 0
    state_read_targets: list[str] = field(default_factory=list)
    state_write_targets: list[str] = field(default_factory=list)
    writes_privileged_state: bool = False
    writes_sensitive_config: bool = False
    state_write_before_external_call: bool = False
    state_write_after_external_call: bool = False
    reads_balance_state: bool = False
    writes_balance_state: bool = False
    reads_share_state: bool = False
    writes_share_state: bool = False

    # =========================================================================
    # 4. External Calls (20 properties)
    # =========================================================================
    has_external_calls: bool = False
    external_call_count: int = 0
    has_internal_calls: bool = False
    internal_call_count: int = 0
    has_low_level_calls: bool = False
    low_level_call_count: int = 0
    low_level_calls: list[str] = field(default_factory=list)
    uses_delegatecall: bool = False
    uses_call: bool = False
    has_call_with_value: bool = False
    has_call_with_gas: bool = False
    has_hardcoded_gas: bool = False
    call_target_user_controlled: bool = False
    call_target_validated: bool = False
    call_data_user_controlled: bool = False
    call_value_user_controlled: bool = False
    checks_low_level_call_success: bool = False
    decodes_call_return: bool = False
    checks_returndata_length: bool = False
    delegatecall_target_user_controlled: bool = False

    # =========================================================================
    # 5. User Input & Parameters (18 properties)
    # =========================================================================
    has_user_input: bool = False
    input_count: int = 0
    parameter_names: list[str] = field(default_factory=list)
    parameter_types: list[str] = field(default_factory=list)
    accepts_address_parameter: bool = False
    has_array_parameter: bool = False
    has_amount_parameter: bool = False
    has_bytes_parameter: bool = False
    has_threshold_parameter: bool = False
    has_pagination_parameter: bool = False
    has_bytes_or_string_parameter: bool = False
    has_bytes_length_check: bool = False
    has_nonce_parameter: bool = False
    has_fee_parameter: bool = False
    has_fee_bounds: bool = False
    has_duration_parameter: bool = False
    has_duration_bounds: bool = False
    has_timelock_parameter: bool = False

    # =========================================================================
    # 6. Context Variables (12 properties)
    # =========================================================================
    uses_msg_sender: bool = False
    uses_tx_origin: bool = False
    uses_msg_value: bool = False
    uses_block_timestamp: bool = False
    uses_block_number: bool = False
    uses_block_hash: bool = False
    uses_block_prevrandao: bool = False
    uses_chainid: bool = False
    uses_ecrecover: bool = False
    tx_origin_in_require: bool = False
    reads_nonce_state: bool = False
    writes_nonce_state: bool = False

    # =========================================================================
    # 7. Token Operations (24 properties)
    # =========================================================================
    token_call_kinds: list[str] = field(default_factory=list)
    uses_erc20_transfer: bool = False
    uses_erc20_transfer_from: bool = False
    uses_erc20_approve: bool = False
    approves_infinite_amount: bool = False
    uses_erc20_mint: bool = False
    uses_erc20_burn: bool = False
    uses_erc721_safe_transfer: bool = False
    uses_erc721_safe_mint: bool = False
    uses_erc1155_safe_transfer: bool = False
    uses_erc1155_safe_batch_transfer: bool = False
    uses_erc1155_mint: bool = False
    uses_erc1155_mint_batch: bool = False
    uses_erc777_send: bool = False
    uses_erc777_operator_send: bool = False
    uses_erc777_burn: bool = False
    uses_erc777_mint: bool = False
    uses_erc4626_deposit: bool = False
    uses_erc4626_withdraw: bool = False
    uses_erc4626_redeem: bool = False
    uses_erc4626_mint: bool = False
    uses_safe_erc20: bool = False
    checks_token_call_return: bool = False
    token_return_guarded: bool = False

    # =========================================================================
    # 8. Oracle & Price (22 properties)
    # =========================================================================
    reads_oracle_price: bool = False
    reads_dex_reserves: bool = False
    reads_pool_reserves: bool = False
    oracle_call_count: int = 0
    oracle_source_count: int = 0
    oracle_source_targets: list[str] = field(default_factory=list)
    has_staleness_check: bool = False
    has_staleness_threshold: bool = False
    oracle_round_check: bool = False
    oracle_freshness_ok: bool = False
    calls_chainlink_latest_round_data: bool = False
    calls_chainlink_decimals: bool = False
    validates_answer_positive: bool = False
    validates_updated_at_recent: bool = False
    validates_started_at_recent: bool = False
    validates_answered_in_round_matches_round_id: bool = False
    handles_oracle_revert: bool = False
    has_multi_source_oracle: bool = False
    reads_twap: bool = False
    has_twap_window_parameter: bool = False
    reads_twap_with_window: bool = False
    has_twap_validation: bool = False

    # =========================================================================
    # 9. Deadline & Slippage (12 properties)
    # =========================================================================
    has_deadline_check: bool = False
    has_deadline_parameter: bool = False
    has_deadline_future_check: bool = False
    has_deadline_min_buffer: bool = False
    has_deadline_max: bool = False
    has_slippage_parameter: bool = False
    has_slippage_check: bool = False
    has_minimum_output_parameter: bool = False
    has_minimum_output: bool = False
    has_timelock_check: bool = False
    swap_like: bool = False
    performs_swap: bool = False

    # =========================================================================
    # 10. Loop Analysis (12 properties)
    # =========================================================================
    has_loops: bool = False
    loop_count: int = 0
    max_loop_depth: int = 0
    has_nested_loop: bool = False
    loop_bound_sources: list[str] = field(default_factory=list)
    has_unbounded_loop: bool = False
    has_require_bounds: bool = False
    external_calls_in_loop: bool = False
    has_delete_in_loop: bool = False
    has_unbounded_deletion: bool = False
    event_emission_in_loop: bool = False
    mapping_iteration_in_loop: bool = False

    # =========================================================================
    # 11. Arithmetic & Precision (28 properties)
    # =========================================================================
    uses_arithmetic: bool = False
    uses_division: bool = False
    uses_unchecked_block: bool = False
    has_unchecked_block: bool = False
    unchecked_contains_arithmetic: bool = False
    unchecked_operand_from_user: bool = False
    unchecked_affects_balance: bool = False
    has_arithmetic: bool = False
    has_division: bool = False
    has_multiplication: bool = False
    division_before_multiplication: bool = False
    divisor_source: list[str] = field(default_factory=list)
    divisor_validated_nonzero: bool = False
    has_precision_guard: bool = False
    has_rounding_ops: bool = False
    large_number_multiplication: bool = False
    price_amount_multiplication: bool = False
    percentage_calculation: bool = False
    percentage_bounds_check: bool = False
    basis_points_calculation: bool = False
    ratio_calculation: bool = False
    fee_calculation: bool = False
    fee_accumulation: bool = False
    timestamp_arithmetic: bool = False
    uses_token_decimals: bool = False
    decimal_scaling_usage: bool = False
    uses_safemath: bool = False
    uses_muldiv_or_safemath: bool = False

    # =========================================================================
    # 12. Reentrancy (6 properties)
    # =========================================================================
    callback_chain_surface: bool = False
    protocol_callback_chain_surface: bool = False
    callback_entrypoint_surface: bool = False
    token_callback_surface: bool = False
    cross_function_reentrancy_surface: bool = False
    cross_function_reentrancy_read: bool = False

    # =========================================================================
    # 13. Function Classification (16 properties)
    # =========================================================================
    is_withdraw_like: bool = False
    is_deposit_like: bool = False
    is_mint_like: bool = False
    is_burn_like: bool = False
    is_reward_like: bool = False
    is_liquidation_like: bool = False
    is_callback: bool = False
    is_upgrade_function: bool = False
    is_initializer_function: bool = False
    is_permit_like: bool = False
    is_admin_named: bool = False
    is_emergency_function: bool = False
    is_multicall_function: bool = False
    is_timelock_admin_function: bool = False
    is_privileged_operation: bool = False
    is_value_transfer: bool = False

    # =========================================================================
    # 14. Flash Loan (8 properties)
    # =========================================================================
    flash_loan_callback: bool = False
    flash_loan_validation: bool = False
    flash_loan_initiator_checked: bool = False
    flash_loan_repayment_checked: bool = False
    flash_loan_asset_checked: bool = False
    flash_loan_guard: bool = False
    flash_loan_sensitive_operation: bool = False
    uses_balance_of: bool = False

    # =========================================================================
    # 15. Semantic Operations (4 properties)
    # =========================================================================
    semantic_ops: list[str] = field(default_factory=list)
    op_sequence: list[dict[str, Any]] = field(default_factory=list)
    behavioral_signature: str = ""
    op_ordering: list[tuple[str, str]] = field(default_factory=list)

    # =========================================================================
    # 16. Source Location (3 properties)
    # =========================================================================
    file: str | None = None
    line_start: int | None = None
    line_end: int | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for node properties.

        Returns:
            Dictionary containing all properties suitable for Node.properties.
        """
        return {k: v for k, v in self.__dict__.items() if not k.startswith("_")}


class FunctionProcessor:
    """Process functions and compute security properties.

    This class extracts the function analysis logic from builder_legacy.py,
    organizing it into logical method groups for maintainability.

    The main entry point is `process_all()` which processes all functions
    for a contract and returns the created nodes.
    """

    def __init__(self, ctx: "BuildContext") -> None:
        """Initialize the function processor.

        Args:
            ctx: Build context with shared state and configuration.
        """
        self.ctx = ctx
        # Import legacy builder for delegated methods (transitional)
        # This allows incremental migration - we can move methods one by one
        from alphaswarm_sol.kg.builder_legacy import VKGBuilder
        self._legacy = VKGBuilder(ctx.project_root, exclude_dependencies=ctx.exclude_dependencies)
        self._legacy._source_cache = ctx.source_cache

    def process_all(
        self,
        contract: Any,
        contract_node: Node,
    ) -> list[Node]:
        """Process all functions for a contract.

        Args:
            contract: Slither contract object.
            contract_node: The contract's Node in the graph.

        Returns:
            List of function nodes created.
        """
        nodes = []

        # Skip interfaces
        if getattr(contract, "is_interface", False):
            return nodes

        functions = getattr(contract, "functions", []) or []

        for fn in functions:
            node = self.process(fn, contract, contract_node)
            if node:
                nodes.append(node)

        return nodes

    def process(
        self,
        fn: Any,
        contract: Any,
        contract_node: Node,
    ) -> Node | None:
        """Process a single function and create its node.

        This is the main processing method that computes all properties
        for a function and creates its graph node.

        Args:
            fn: Slither function object.
            contract: Slither contract object.
            contract_node: The contract's Node in the graph.

        Returns:
            The created function Node, or None if processing failed.
        """
        # Get source location
        file_path, line_start, line_end = source_location(fn)
        if file_path:
            file_path = relpath(file_path, self.ctx.project_root)

        label = function_label(fn)

        # Compute all properties using legacy builder methods (transitional)
        # This delegates to the existing implementation while we're migrating
        props = self._compute_all_properties(fn, contract, contract_node, file_path, line_start, line_end, label)

        # Generate node ID
        node_id = node_id_hash("function", f"{contract.name}.{label}", file_path, line_start)

        # Create the node
        node = Node(
            id=node_id,
            type="Function",
            label=label,
            properties=props,
            evidence=evidence_from_location(file_path, line_start, line_end),
        )

        # Add to graph
        self.ctx.graph.add_node(node)

        # Add CONTAINS_FUNCTION edge
        self.ctx.graph.add_edge(
            Edge(
                id=edge_id_hash("CONTAINS_FUNCTION", contract_node.id, node_id),
                type="CONTAINS_FUNCTION",
                source=contract_node.id,
                target=node_id,
                evidence=evidence_from_location(file_path, line_start, line_end),
            )
        )

        # Create relationship edges using legacy methods
        self._legacy._link_modifiers(self.ctx.graph, fn, node)
        self._legacy._link_state_vars(self.ctx.graph, fn, node, contract)
        self._legacy._link_calls(self.ctx.graph, fn, node)
        self._legacy._link_external_callsites(self.ctx.graph, fn, node)

        # Link signature use
        self._legacy._link_signature_use(
            self.ctx.graph,
            fn_node=node,
            uses_ecrecover=props.get("uses_ecrecover", False),
            uses_chainid=props.get("uses_chainid", False),
            has_nonce_parameter=props.get("has_nonce_parameter", False),
        )

        # Analyze and link loops
        loop_summary, loop_nodes = self._legacy._analyze_loops(
            fn,
            props.get("parameter_names", []),
            getattr(fn, "state_variables_read", []) or [],
        )
        self._legacy._link_loops(self.ctx.graph, node, loop_nodes)

        # Augment with taint information
        input_sources = extract_inputs(fn)
        special_sources = extract_special_sources(fn)
        self._legacy._augment_taint(self.ctx.graph, fn, contract, node, input_sources, special_sources)

        return node

    def _compute_all_properties(
        self,
        fn: Any,
        contract: Any,
        contract_node: Node,
        file_path: str | None,
        line_start: int | None,
        line_end: int | None,
        label: str,
    ) -> dict[str, Any]:
        """Compute all properties for a function.

        This method delegates to the legacy builder during the transition period.
        The properties computation is complex (~1000 LOC) and will be migrated
        incrementally in future plans.

        Args:
            fn: Slither function object.
            contract: Slither contract object.
            contract_node: The contract's Node in the graph.
            file_path: Function source file path.
            line_start: Starting line number.
            line_end: Ending line number.
            label: Function label.

        Returns:
            Dictionary of all computed properties.
        """
        # For transitional period, delegate to legacy builder
        # This method would be called by _add_functions in legacy builder
        # We extract the properties computation here

        # Get contract-level context
        functions = getattr(contract, "functions", []) or []
        function_names = [f.name for f in functions if getattr(f, "name", None)]
        lowered_function_names = [name.lower() for name in function_names]
        state_vars = getattr(contract, "state_variables", []) or []
        state_var_names = [getattr(var, "name", "") for var in state_vars if getattr(var, "name", None)]
        lowered_state_var_names = [(getattr(var, "name", "") or "").lower() for var in state_vars]

        # Contract-level properties
        contract_is_proxy_like = "proxy" in contract.name.lower() or "upgradeable" in contract.name.lower()
        contract_has_upgrade_function = any(name.lower().startswith("upgrade") for name in function_names)
        contract_proxy_type = self._legacy._detect_proxy_type(contract)
        contract_is_uups_proxy = contract_proxy_type == "uups"
        contract_is_beacon_proxy = contract_proxy_type == "beacon"
        contract_is_diamond_proxy = "diamond" in contract.name.lower() or any(
            "diamond" in base.name.lower()
            for base in getattr(contract, "inheritance", []) or []
            if getattr(base, "name", None)
        )
        contract_is_implementation_contract = (not contract_is_proxy_like) and (
            contract_has_upgrade_function
            or "implementation" in contract.name.lower()
            or "logic" in contract.name.lower()
        )
        contract_is_upgradeable = bool(
            contract_is_proxy_like or contract_has_upgrade_function or contract_is_implementation_contract
        )
        contract_has_multicall = any("multicall" in name.lower() for name in function_names)
        contract_has_beacon_state = any("beacon" in name.lower() for name in state_var_names if name)

        # Contract governance/security signals
        contract_has_multisig = "multisig" in contract.name.lower() or any(
            token in name for token in ("multisig", "multi_sig", "threshold", "signer", "signers", "owners")
            for name in lowered_state_var_names
        )
        contract_has_governance = self._legacy._has_governance_signals(state_vars, lowered_function_names)
        contract_has_timelock = any(
            "timelock" in name or "time_lock" in name for name in lowered_state_var_names
        ) or any("timelock" in name.lower() for name in function_names)
        contract_has_withdraw = any(
            any(token in name for token in ("withdraw", "claim", "redeem", "release"))
            for name in lowered_function_names
        )
        contract_has_emergency_withdraw = any(
            "emergency" in name and any(token in name for token in ("withdraw", "rescue", "recover"))
            for name in lowered_function_names
        )
        contract_has_emergency_pause = any("pause" in name for name in lowered_function_names)

        # Compiler version from contract node
        compiler_version_lt_08 = bool(contract_node.properties.get("compiler_version_lt_08"))
        contract_uses_safemath = bool(contract_node.properties.get("uses_safemath"))

        # Array/mapping state vars
        mapping_state_var_names = [
            getattr(var, "name", "")
            for var in state_vars
            if "mapping" in str(getattr(var, "type", "") or "").lower()
        ]
        array_state_var_names = [
            getattr(var, "name", "")
            for var in state_vars
            if "[]" in str(getattr(var, "type", "") or "").lower()
            or "array" in str(getattr(var, "type", "") or "").lower()
        ]

        # State machine vars
        state_machine_vars = self._legacy._state_machine_var_names(state_vars)

        # Contract inheritance/composition
        contract_has_inheritance = bool(getattr(contract, "inheritance", []) or [])
        contract_has_composition = self._legacy._contract_has_composition(contract)
        contract_has_balance_tracking = self._legacy._contract_has_balance_tracking(contract)

        # =============================================================
        # Function-level analysis starts here
        # =============================================================

        # Basic function info
        modifiers = [m.name for m in getattr(fn, "modifiers", []) if getattr(m, "name", None)]
        access_gate_mods = [m for m in modifiers if is_access_gate(m)]
        auth_patterns = self._legacy.classify_auth_modifiers(modifiers) if hasattr(self._legacy, "classify_auth_modifiers") else []

        # For auth_patterns, import from heuristics if not on legacy
        from alphaswarm_sol.kg.heuristics import classify_auth_modifiers
        auth_patterns = classify_auth_modifiers(modifiers)

        has_only_owner = any(
            "onlyowner" in m.lower() or ("only" in m.lower() and "owner" in m.lower())
            for m in modifiers
        )
        has_only_role = any(
            "onlyrole" in m.lower() or ("only" in m.lower() and "role" in m.lower())
            for m in modifiers
        )

        # External/internal calls
        external_calls = getattr(fn, "external_calls", []) or []
        high_level_calls = getattr(fn, "high_level_calls", []) or []
        internal_calls = getattr(fn, "internal_calls", []) or []
        low_level_calls = getattr(fn, "low_level_calls", []) or []

        visibility = getattr(fn, "visibility", None)
        calls_internal_functions = bool(internal_calls)

        # State reads/writes
        reads_state = getattr(fn, "state_variables_read", []) or []
        writes_state = getattr(fn, "state_variables_written", []) or []
        state_read_targets = self._legacy._classify_state_read_targets(reads_state)
        state_write_targets = self._legacy._classify_state_write_targets(writes_state)

        writes_privileged_state = any(is_privileged_state(tags) for tags in state_write_targets.values())
        writes_sensitive_config = any(
            tag in {"fee", "config", "reward", "collateral", "debt", "liquidity", "reserve",
                    "cap", "oracle", "treasury", "governance", "pause", "allowlist", "denylist",
                    "signer", "dependency"}
            for tags in state_write_targets.values()
            for tag in tags
        )

        # Low-level call analysis
        low_level_names = []
        for call in low_level_calls:
            for attr in ("name", "function_name", "full_name"):
                name = getattr(call, attr, None)
                if name:
                    low_level_names.append(str(name))
        low_level_names = [name for name in low_level_names if name]
        uses_delegatecall = any("delegatecall" in name.lower() for name in low_level_names)
        uses_call = any(name.lower() in {"call", "staticcall"} for name in low_level_names)

        has_external_calls = bool(external_calls) or bool(low_level_calls) or bool(high_level_calls)

        # Input analysis
        input_sources = extract_inputs(fn)
        has_user_input = bool(input_sources)

        # Parameters
        parameters = getattr(fn, "parameters", []) or []
        parameter_names = [getattr(p, "name", None) for p in parameters if getattr(p, "name", None)]
        parameter_types = [str(getattr(p, "type", "") or "") for p in parameters]

        # Parameter classification
        param_classification = classify_parameter_types(parameters)
        address_param_names = param_classification["address"]
        array_param_names = param_classification["array"]
        amount_param_names = param_classification["amount"]
        bytes_param_names = param_classification["bytes"]
        threshold_param_names = param_classification["threshold"]

        accepts_address_parameter = bool(address_param_names)
        has_array_parameter = bool(array_param_names)
        has_amount_parameter = bool(amount_param_names)
        has_bytes_parameter = bool(bytes_param_names)
        has_threshold_parameter = bool(threshold_param_names)
        has_pagination_parameter = bool(param_classification["pagination"])
        has_nonce_parameter = bool(param_classification["nonce"])

        # Context variables
        variables_read = getattr(fn, "variables_read", []) or []
        uses_msg_sender = uses_var_name(variables_read, "msg.sender")
        uses_tx_origin = uses_var_name(variables_read, "tx.origin")
        uses_msg_value = uses_var_name(variables_read, "msg.value")
        uses_block_timestamp = uses_var_name(variables_read, "block.timestamp")
        uses_block_number = uses_var_name(variables_read, "block.number")
        uses_block_hash = uses_var_name(variables_read, "blockhash")
        uses_block_prevrandao = uses_var_name(variables_read, "block.prevrandao")
        uses_chainid = uses_var_name(variables_read, "block.chainid")

        solidity_calls = getattr(fn, "solidity_calls", []) or []
        uses_ecrecover = any("ecrecover" in str(call) for call in solidity_calls)

        # Call order analysis
        call_order = self._legacy._infer_call_order(fn)

        # Access gate analysis
        access_gate_logic, access_gate_sources = self._legacy._access_gate_from_predicates(fn)
        has_access_gate = bool(access_gate_mods) or access_gate_logic
        has_access_modifier = bool(access_gate_mods)
        has_require_msg_sender = "msg.sender" in access_gate_sources

        # Nonce state
        reads_nonce_state = self._legacy._state_var_name_match(reads_state, "nonce")
        writes_nonce_state = self._legacy._state_var_name_match(writes_state, "nonce")
        uses_domain_separator = self._legacy._state_var_name_match(reads_state, "domain_separator")

        # Require expressions
        require_exprs = self._legacy._require_expressions(fn)
        tx_origin_in_require = self._legacy._tx_origin_in_require(require_exprs)

        # Deadline/timelock checks
        has_deadline_check = self._legacy._has_deadline_check(require_exprs, parameter_names)
        has_deadline_future_check = self._legacy._has_deadline_future_check(require_exprs, parameter_names)
        has_deadline_min_buffer = self._legacy._has_deadline_min_buffer(require_exprs, parameter_names)
        has_deadline_max = self._legacy._has_deadline_max(require_exprs, parameter_names)
        has_initializer_modifier = self._legacy._has_initializer_modifier(modifiers)
        has_only_proxy_modifier = self._legacy._has_only_proxy_modifier(modifiers)
        checks_initialized_flag = self._legacy._checks_initialized_flag(require_exprs)
        access_control_uses_or = self._legacy._access_gate_uses_or(require_exprs)
        time_based_access_control = self._legacy._has_block_timestamp_check(require_exprs)
        validates_delegatecall_target = self._legacy._validates_delegatecall_target(require_exprs, parameter_names)
        call_target_validated = self._legacy._validates_call_target(require_exprs, address_param_names)
        has_timelock_parameter = self._legacy._has_timelock_parameter(parameter_names)
        has_timelock_check = self._legacy._has_timelock_check(require_exprs, parameter_names)

        # Permit/signature
        is_permit_like = "permit" in (getattr(fn, "name", "") or "").lower()

        # Token calls
        token_call_kinds = self._legacy._token_call_kinds(fn)

        # Reentrancy guard
        has_reentrancy_guard = self._legacy._has_reentrancy_guard(modifiers, require_exprs)

        # Token operations
        uses_erc20_transfer = "transfer" in token_call_kinds
        uses_erc20_transfer_from = "transferfrom" in token_call_kinds
        uses_erc20_approve = "approve" in token_call_kinds
        uses_erc20_mint = "mint" in token_call_kinds
        uses_erc20_burn = "burn" in token_call_kinds
        uses_erc721_safe_transfer = "safetransferfrom" in token_call_kinds
        uses_erc721_safe_mint = "safemint" in token_call_kinds
        uses_erc1155_safe_transfer = "safetransferfrom" in token_call_kinds
        uses_erc1155_safe_batch_transfer = "safebatchtransferfrom" in token_call_kinds
        uses_erc1155_mint = "mint" in token_call_kinds
        uses_erc1155_mint_batch = "mintbatch" in token_call_kinds
        uses_erc777_send = "send" in token_call_kinds
        uses_erc777_operator_send = "operatorsend" in token_call_kinds
        uses_erc777_burn = "burn" in token_call_kinds
        uses_erc777_mint = "mint" in token_call_kinds
        uses_erc4626_deposit = "deposit" in token_call_kinds
        uses_erc4626_withdraw = "withdraw" in token_call_kinds
        uses_erc4626_redeem = "redeem" in token_call_kinds
        uses_erc4626_mint = "mint" in token_call_kinds
        uses_safe_erc20 = any(kind.startswith("safe") for kind in token_call_kinds)
        checks_token_call_return = self._legacy._checks_token_call_return(require_exprs)
        checks_zero_address = self._legacy._checks_zero_address(require_exprs)

        # Oracle analysis
        reads_oracle_price = self._legacy._reads_oracle_price(token_call_kinds)
        reads_dex_reserves = "getreserves" in token_call_kinds
        reads_pool_reserves = reads_dex_reserves
        oracle_call_count = self._legacy._oracle_call_count(fn)
        oracle_source_targets = sorted(self._legacy._oracle_call_targets(high_level_calls))
        has_staleness_check = self._legacy._has_staleness_check(require_exprs)
        has_staleness_threshold = self._legacy._has_staleness_threshold(require_exprs)
        has_deadline_parameter = self._legacy._has_deadline_parameter(parameter_names)
        has_slippage_parameter = self._legacy._has_slippage_parameter(parameter_names)
        has_slippage_check = self._legacy._has_slippage_check(require_exprs, parameter_names)
        has_sequencer_uptime_check = self._legacy._has_sequencer_uptime_check(require_exprs)
        has_sequencer_grace_period = self._legacy._has_sequencer_grace_period(require_exprs)
        oracle_round_check = self._legacy._has_oracle_round_check(require_exprs)
        oracle_freshness_ok = bool(has_staleness_check and oracle_round_check)
        calls_chainlink_latest_round_data = "latestrounddata" in token_call_kinds
        calls_chainlink_decimals = "decimals" in token_call_kinds
        validates_answer_positive = self._legacy._validates_oracle_answer_positive(require_exprs)
        validates_updated_at_recent = self._legacy._validates_oracle_timestamp(require_exprs)
        has_v3_struct_params = self._legacy._has_v3_struct_params(fn)

        # Swap detection
        swap_like = self._legacy._is_swap_like(getattr(fn, "name", "") or "", token_call_kinds, parameter_names)

        # State mutability
        state_mutability = normalize_state_mutability(fn)
        is_view = state_mutability == "view"

        # Function classification
        is_withdraw_like = self._legacy._is_withdraw_like(getattr(fn, "name", "") or "")
        is_deposit_like = self._legacy._is_deposit_like(getattr(fn, "name", "") or "")
        is_mint_like = self._legacy._is_mint_like(getattr(fn, "name", "") or "")
        is_burn_like = self._legacy._is_burn_like(getattr(fn, "name", "") or "")
        is_reward_like = self._legacy._is_reward_like(getattr(fn, "name", "") or "")
        is_liquidation_like = self._legacy._is_liquidation_like(getattr(fn, "name", "") or "")
        is_callback = self._legacy._is_callback_function(fn)
        is_upgrade_function = self._legacy._is_upgrade_function(fn)
        is_initializer_function = self._legacy._is_initializer_function(fn)

        # Balance checks
        uses_balance_of = "balanceof" in token_call_kinds
        uses_total_supply = "totalsupply" in token_call_kinds
        has_balance_check = self._legacy._has_balance_check(require_exprs)
        checks_received_amount = self._legacy._checks_received_amount(require_exprs)
        has_pause_check = self._legacy._has_pause_check(require_exprs)
        uses_allowance_adjust = self._legacy._uses_allowance_adjust(token_call_kinds)

        # Source text analysis
        source_text = get_source_slice(file_path, line_start, line_end, self.ctx.project_root, self.ctx.source_cache)
        source_text_lower = source_text.lower()
        source_text_clean = strip_comments(source_text_lower)

        # Computations that need source text
        approves_infinite_amount = uses_erc20_approve and self._legacy._approves_infinite_amount(source_text_clean)
        has_strict_equality_check = self._legacy._has_strict_equality_check(require_exprs, source_text_clean)

        # Loop analysis
        loop_summary, loop_nodes = self._legacy._analyze_loops(fn, parameter_names, reads_state)
        has_nested_loop = bool(
            loop_summary["has_nested_loop"] or self._legacy._has_nested_loop_text(source_text_clean)
        )

        # Token return guard
        custom_return_guard = self._legacy._has_custom_return_guard(source_text_lower)
        token_return_guarded = bool(
            checks_token_call_return or uses_safe_erc20 or custom_return_guard
        )

        # TWAP analysis
        reads_twap = self._legacy._reads_twap(token_call_kinds, source_text_lower)
        has_twap_window_parameter = self._legacy._has_twap_window_parameter(parameter_names)
        reads_twap_with_window = reads_twap and has_twap_window_parameter
        has_twap_validation = bool(reads_twap or reads_twap_with_window)

        # Flash loan analysis
        flash_loan_callback = self._legacy._is_flash_loan_callback(getattr(fn, "name", "") or "")
        flash_loan_initiator_checked = self._legacy._has_flash_loan_initiator_check(require_exprs)
        flash_loan_repayment_checked = self._legacy._has_flash_loan_repayment_check(require_exprs)
        flash_loan_asset_checked = self._legacy._has_flash_loan_asset_check(require_exprs)
        flash_loan_validation = bool(
            flash_loan_initiator_checked
            and flash_loan_repayment_checked
            and flash_loan_asset_checked
        )
        flash_loan_guard = self._legacy._has_flash_loan_guard(modifiers)
        flash_loan_sensitive_operation = bool(reads_oracle_price or reads_dex_reserves or reads_twap or swap_like)

        # Low-level call summary
        low_level_summary = self._legacy._summarize_low_level_calls(
            low_level_calls,
            parameter_names,
            require_exprs,
            getattr(fn, "nodes", []) or [],
        )

        # Transfer operations
        uses_transfer = self._legacy._uses_transfer(fn)
        uses_send = self._legacy._uses_send(fn)
        transfers_eth = uses_transfer or uses_send or low_level_summary["has_call_with_value"]

        # Admin/emergency classification
        is_admin_named = self._legacy._is_admin_named_function(label)
        is_emergency_function = self._legacy._is_emergency_function(label)
        is_multicall_function = "multicall" in label.lower()
        is_timelock_admin_function = self._legacy._is_timelock_admin_function(label)

        # Access control properties
        has_access_control = bool(
            has_access_gate or has_access_modifier or has_only_owner or has_only_role
        )

        # Require bounds
        has_require_bounds = self._legacy._has_require_bounds(require_exprs, parameter_names)

        # Semgrep rules
        semgrep_rules = detect_semgrep_function_rules(
            FunctionContext(
                name=label,
                visibility=getattr(fn, "visibility", None),
                mutability=state_mutability,
                has_access_gate=has_access_gate,
                has_reentrancy_guard=has_reentrancy_guard,
                has_user_input=has_user_input,
                uses_call=uses_call,
                uses_delegatecall=uses_delegatecall,
                has_external_calls=has_external_calls,
                uses_msg_value=uses_msg_value,
                uses_ecrecover=uses_ecrecover,
                uses_block_hash=uses_block_hash,
                call_target_user_controlled=low_level_summary["call_target_user_controlled"],
                call_data_user_controlled=low_level_summary["call_data_user_controlled"],
                call_value_user_controlled=low_level_summary["call_value_user_controlled"],
                delegatecall_target_user_controlled=low_level_summary["delegatecall_target_user_controlled"],
                reads_state=bool(reads_state),
                reads_dex_reserves=reads_dex_reserves,
                reads_twap_with_window=reads_twap_with_window,
                has_slippage_check=has_slippage_check,
                swap_like=swap_like,
                uses_erc20_transfer=uses_erc20_transfer,
                uses_erc20_transfer_from=uses_erc20_transfer_from,
                uses_erc20_burn=uses_erc20_burn,
                uses_erc721_safe_transfer=uses_erc721_safe_transfer,
                uses_erc777_send=uses_erc777_send,
                uses_erc777_operator_send=uses_erc777_operator_send,
                state_write_after_external_call=call_order.get("write_after_call"),
                has_loops=loop_summary["has_loops"],
                is_constructor=bool(getattr(fn, "is_constructor", None)),
                payable=getattr(fn, "payable", None),
                writes_state=bool(writes_state),
                parameter_types=parameter_types,
                require_exprs=require_exprs,
                source=source_text,
            )
        )
        semgrep_security_count = len([rule for rule in semgrep_rules if rule in SECURITY_RULES])

        # Semantic operations
        semantic_ops_list = derive_all_operations(fn)
        semantic_op_names = [op.operation.name for op in semantic_ops_list]
        op_sequence = [
            {"op": op.operation.name, "order": op.cfg_order, "line": op.line_number}
            for op in sorted(semantic_ops_list, key=lambda x: x.cfg_order)
        ]
        behavioral_signature = compute_behavioral_signature(semantic_ops_list)
        op_ordering = compute_ordering_pairs(semantic_ops_list)

        # State tag helpers
        def has_state_tag(targets: dict[str, list[str]], tag: str) -> bool:
            return any(tag in tags for tags in targets.values())

        reads_balance_state = has_state_tag(state_read_targets, "balance")
        writes_balance_state = has_state_tag(state_write_targets, "balance")
        reads_share_state = has_state_tag(state_read_targets, "shares")
        writes_share_state = has_state_tag(state_write_targets, "shares")
        reads_supply_state = has_state_tag(state_read_targets, "supply")
        writes_supply_state = has_state_tag(state_write_targets, "supply")

        # =====================================================================
        # Properties previously only in builder_legacy.py — migrated for parity
        # =====================================================================

        # Arithmetic & precision properties
        uses_unchecked_block = "unchecked" in source_text_lower
        uses_arithmetic = self._legacy._uses_arithmetic(source_text_lower)
        uses_division = self._legacy._uses_division(source_text_lower)
        has_unchecked_block = uses_unchecked_block
        has_arithmetic = self._legacy._has_arithmetic_ops(source_text_lower)
        has_division = self._legacy._has_division(source_text_lower)
        has_multiplication = self._legacy._has_multiplication(source_text_lower)
        division_before_multiplication = self._legacy._division_before_multiplication(source_text_lower)
        divisor_source = self._legacy._divisor_sources(source_text_lower, parameter_names, state_var_names)
        divisor_validated_nonzero = self._legacy._divisor_validated_nonzero(require_exprs, parameter_names) if hasattr(self._legacy, "_divisor_validated_nonzero") else self._legacy._has_nonzero_check(require_exprs, parameter_names + state_var_names)
        has_precision_guard = self._legacy._has_precision_guard(require_exprs, source_text_lower)
        has_rounding_ops = self._legacy._has_rounding_ops(source_text_lower)
        large_number_multiplication = self._legacy._large_number_multiplication(source_text_lower)
        price_amount_multiplication = self._legacy._price_amount_multiplication(source_text_lower)
        percentage_calculation = self._legacy._percentage_calculation(source_text_lower)
        percentage_bounds_check = self._legacy._percentage_bounds_check(require_exprs, parameter_names)
        basis_points_calculation = self._legacy._basis_points_calculation(source_text_lower)
        ratio_calculation = self._legacy._ratio_calculation(source_text_lower)
        fee_calculation = self._legacy._fee_calculation(source_text_lower)
        fee_accumulation = self._legacy._fee_accumulation(source_text_lower)
        timestamp_arithmetic = self._legacy._timestamp_arithmetic(source_text_lower)
        uses_token_decimals = self._legacy._uses_token_decimals(source_text_lower)
        decimal_scaling_usage = self._legacy._decimal_scaling_usage(source_text_lower)
        uses_safemath = bool(contract_uses_safemath or "safemath" in source_text_lower)
        uses_muldiv_or_safemath = self._legacy._uses_muldiv_or_safemath(source_text_lower)
        unchecked_contains_arithmetic = bool(has_unchecked_block and has_arithmetic)
        unchecked_operand_from_user = self._legacy._unchecked_uses_parameters(source_text_lower, parameter_names)
        unchecked_affects_balance = bool(
            has_unchecked_block
            and (reads_balance_state or writes_balance_state)
        )

        # Parameter classification properties
        string_param_names = [
            name
            for name, type_name in zip(parameter_names, parameter_types)
            if name and "string" in type_name.lower()
        ]
        bytes_or_string_param_names = bytes_param_names + string_param_names
        has_bytes_or_string_parameter = bool(bytes_or_string_param_names)
        has_bytes_length_check = self._legacy._has_bytes_length_check(
            require_exprs, bytes_or_string_param_names
        )
        has_fee_parameter = any("fee" in name.lower() for name in parameter_names)
        has_fee_bounds = self._legacy._has_named_bounds(require_exprs, parameter_names, {"fee", "fees"})
        has_duration_parameter = self._legacy._has_duration_parameter(parameter_names)
        has_duration_bounds = self._legacy._has_duration_bounds(require_exprs, parameter_names)
        has_minimum_output_parameter = self._legacy._has_slippage_parameter(parameter_names)
        has_minimum_output = has_slippage_check

        # Oracle extended properties
        oracle_source_count = len(oracle_source_targets)
        if reads_oracle_price and oracle_source_count == 0 and oracle_call_count:
            oracle_source_count = 1
        has_multi_source_oracle = oracle_source_count > 1
        validates_started_at_recent = self._legacy._validates_oracle_started_at(require_exprs)

        # Loop properties
        event_emission_in_loop = loop_summary["has_loops"] and "emit " in source_text_lower
        mapping_iteration_in_loop = bool(
            loop_summary["has_loops"]
            and any(
                str(name).lower() in source_text_lower for name in mapping_state_var_names if name
            )
        )

        # Reentrancy surface properties
        external_call_contracts = self._legacy._external_call_contracts(
            external_calls, high_level_calls, contract.name
        )
        calls_external_contract = bool(external_call_contracts)
        reads_dependency_state = has_state_tag(state_read_targets, "dependency")
        callback_chain_surface = bool(
            calls_external_contract
            and has_external_calls
            and call_order.get("write_after_call")
            and not has_reentrancy_guard
        )
        protocol_callback_chain_surface = bool(
            callback_chain_surface
            and (reads_dependency_state or contract_has_composition or contract_has_inheritance)
        )
        callback_entrypoint_surface = bool(
            is_callback
            and calls_external_contract
            and bool(writes_state)
            and not has_reentrancy_guard
        )
        token_callback_surface = any(
            [
                uses_erc721_safe_transfer,
                uses_erc721_safe_mint,
                uses_erc1155_safe_transfer,
                uses_erc1155_safe_batch_transfer,
                uses_erc1155_mint,
                uses_erc1155_mint_batch,
                uses_erc777_send,
                uses_erc777_operator_send,
                uses_erc4626_deposit,
                uses_erc4626_withdraw,
                uses_erc4626_redeem,
                uses_erc4626_mint,
            ]
        )

        # Function classification properties
        is_privileged_operation = bool(writes_privileged_state or uses_transfer or uses_send or uses_call)
        is_value_transfer = bool(
            transfers_eth
            or uses_erc20_transfer
            or uses_erc20_transfer_from
            or uses_erc721_safe_transfer
            or uses_erc1155_safe_transfer
            or uses_erc1155_safe_batch_transfer
        )
        is_pure = state_mutability == "pure"

        # Build properties dictionary
        # This mirrors the structure in builder_legacy.py _add_functions
        props = {
            "visibility": visibility,
            "mutability": getattr(fn, "state_mutability", None),
            "state_mutability": state_mutability,
            "payable": getattr(fn, "payable", None),
            "is_constructor": getattr(fn, "is_constructor", None),
            "is_fallback": getattr(fn, "is_fallback", None),
            "is_receive": getattr(fn, "is_receive", None),
            "signature": getattr(fn, "signature", None),
            "modifiers": modifiers,
            "has_access_gate": has_access_gate,
            "has_access_control": has_access_control,
            "access_gate_modifiers": access_gate_mods,
            "access_gate_logic": access_gate_logic,
            "access_gate_sources": access_gate_sources,
            "has_reentrancy_guard": has_reentrancy_guard,
            "has_only_owner": has_only_owner,
            "has_only_role": has_only_role,
            "auth_patterns": auth_patterns,
            "has_auth_pattern": bool(auth_patterns),
            "external_call_count": len(external_calls),
            "internal_call_count": len(internal_calls),
            "reads_state_count": len(reads_state),
            "writes_state_count": len(writes_state),
            "has_external_calls": has_external_calls,
            "has_untrusted_external_call": bool(
                low_level_summary["call_target_user_controlled"]
                or self._legacy._external_call_target_user_controlled(external_calls, high_level_calls, parameter_names)
            ),
            "has_internal_calls": bool(internal_calls),
            "public_wrapper_without_access_gate": bool(
                visibility in {"public", "external"} and calls_internal_functions and not has_access_gate
            ),
            "reads_state": bool(reads_state),
            "writes_state": bool(writes_state),
            "state_write_targets": sorted({tag for tags in state_write_targets.values() for tag in tags}),
            "state_read_targets": sorted({tag for tags in state_read_targets.values() for tag in tags}),
            "writes_privileged_state": writes_privileged_state,
            "writes_sensitive_config": writes_sensitive_config,
            "low_level_calls": low_level_names,
            "has_low_level_calls": low_level_summary["has_low_level_calls"],
            "low_level_call_count": low_level_summary["low_level_call_count"],
            "uses_delegatecall": uses_delegatecall,
            "uses_call": uses_call,
            "has_call_with_value": low_level_summary["has_call_with_value"],
            "has_call_with_gas": low_level_summary["has_call_with_gas"],
            "has_hardcoded_gas": low_level_summary["has_hardcoded_gas"],
            "call_target_user_controlled": low_level_summary["call_target_user_controlled"],
            "call_target_validated": call_target_validated,
            "call_data_user_controlled": low_level_summary["call_data_user_controlled"],
            "call_value_user_controlled": low_level_summary["call_value_user_controlled"],
            "checks_low_level_call_success": low_level_summary["checks_low_level_call_success"],
            "decodes_call_return": low_level_summary["decodes_call_return"],
            "checks_returndata_length": low_level_summary["checks_returndata_length"],
            "delegatecall_target_user_controlled": low_level_summary["delegatecall_target_user_controlled"],
            "input_count": len(input_sources),
            "has_user_input": has_user_input,
            "parameter_names": parameter_names,
            "parameter_types": parameter_types,
            "accepts_address_parameter": accepts_address_parameter,
            "has_array_parameter": has_array_parameter,
            "has_amount_parameter": has_amount_parameter,
            "has_bytes_parameter": has_bytes_parameter,
            "has_threshold_parameter": has_threshold_parameter,
            "has_pagination_parameter": has_pagination_parameter,
            "has_nonce_parameter": has_nonce_parameter,
            "uses_msg_sender": uses_msg_sender,
            "uses_tx_origin": uses_tx_origin,
            "uses_msg_value": uses_msg_value,
            "uses_block_timestamp": uses_block_timestamp,
            "uses_block_number": uses_block_number,
            "uses_block_hash": uses_block_hash,
            "uses_block_prevrandao": uses_block_prevrandao,
            "uses_chainid": uses_chainid,
            "uses_ecrecover": uses_ecrecover,
            "tx_origin_in_require": tx_origin_in_require,
            "has_require_msg_sender": has_require_msg_sender,
            "reads_nonce_state": reads_nonce_state,
            "writes_nonce_state": writes_nonce_state,
            "uses_domain_separator": uses_domain_separator,
            "has_deadline_check": has_deadline_check,
            "has_initializer_modifier": has_initializer_modifier,
            "has_only_proxy_modifier": has_only_proxy_modifier,
            "checks_initialized_flag": checks_initialized_flag,
            "access_control_uses_or": access_control_uses_or,
            "time_based_access_control": time_based_access_control,
            "validates_delegatecall_target": validates_delegatecall_target,
            "has_timelock_parameter": has_timelock_parameter,
            "has_timelock_check": has_timelock_check,
            "is_permit_like": is_permit_like,
            "token_call_kinds": sorted(token_call_kinds),
            "uses_erc20_transfer": uses_erc20_transfer,
            "uses_erc20_transfer_from": uses_erc20_transfer_from,
            "uses_erc20_approve": uses_erc20_approve,
            "approves_infinite_amount": approves_infinite_amount,
            "uses_erc20_mint": uses_erc20_mint,
            "uses_erc20_burn": uses_erc20_burn,
            "uses_erc721_safe_transfer": uses_erc721_safe_transfer,
            "uses_erc721_safe_mint": uses_erc721_safe_mint,
            "uses_erc1155_safe_transfer": uses_erc1155_safe_transfer,
            "uses_erc1155_safe_batch_transfer": uses_erc1155_safe_batch_transfer,
            "uses_erc1155_mint": uses_erc1155_mint,
            "uses_erc1155_mint_batch": uses_erc1155_mint_batch,
            "uses_erc777_send": uses_erc777_send,
            "uses_erc777_operator_send": uses_erc777_operator_send,
            "uses_erc777_burn": uses_erc777_burn,
            "uses_erc777_mint": uses_erc777_mint,
            "uses_erc4626_deposit": uses_erc4626_deposit,
            "uses_erc4626_withdraw": uses_erc4626_withdraw,
            "uses_erc4626_redeem": uses_erc4626_redeem,
            "uses_erc4626_mint": uses_erc4626_mint,
            "uses_safe_erc20": uses_safe_erc20,
            "checks_token_call_return": checks_token_call_return,
            "token_return_guarded": token_return_guarded,
            "uses_balance_of": uses_balance_of,
            "uses_total_supply": uses_total_supply,
            "checks_zero_address": checks_zero_address,
            "reads_oracle_price": reads_oracle_price,
            "reads_dex_reserves": reads_dex_reserves,
            "reads_pool_reserves": reads_pool_reserves,
            "has_staleness_check": has_staleness_check,
            "has_staleness_threshold": has_staleness_threshold,
            "has_deadline_parameter": has_deadline_parameter,
            "has_deadline_future_check": has_deadline_future_check,
            "has_deadline_min_buffer": has_deadline_min_buffer,
            "has_deadline_max": has_deadline_max,
            "has_slippage_parameter": has_slippage_parameter,
            "has_slippage_check": has_slippage_check,
            "reads_twap": reads_twap,
            "has_twap_window_parameter": has_twap_window_parameter,
            "reads_twap_with_window": reads_twap_with_window,
            "has_twap_validation": has_twap_validation,
            "has_sequencer_uptime_check": has_sequencer_uptime_check,
            "has_sequencer_grace_period": has_sequencer_grace_period,
            "oracle_round_check": oracle_round_check,
            "oracle_freshness_ok": oracle_freshness_ok,
            "calls_chainlink_latest_round_data": calls_chainlink_latest_round_data,
            "calls_chainlink_decimals": calls_chainlink_decimals,
            "validates_answer_positive": validates_answer_positive,
            "validates_updated_at_recent": validates_updated_at_recent,
            "validates_answered_in_round_matches_round_id": oracle_round_check,
            "handles_oracle_revert": bool(self._legacy._has_try_catch(source_text) if hasattr(self._legacy, "_has_try_catch") else "try " in source_text and "catch" in source_text),
            "has_try_catch": "try " in source_text and "catch" in source_text,
            "has_v3_struct_params": has_v3_struct_params,
            "swap_like": swap_like,
            "performs_swap": swap_like,
            "is_view": is_view,
            "is_withdraw_like": is_withdraw_like,
            "is_deposit_like": is_deposit_like,
            "is_mint_like": is_mint_like,
            "is_burn_like": is_burn_like,
            "is_reward_like": is_reward_like,
            "is_liquidation_like": is_liquidation_like,
            "is_callback": is_callback,
            "is_upgrade_function": is_upgrade_function,
            "is_initializer_function": is_initializer_function,
            "is_permit_like": is_permit_like,
            "is_admin_named": is_admin_named,
            "is_emergency_function": is_emergency_function,
            "is_multicall_function": is_multicall_function,
            "is_timelock_admin_function": is_timelock_admin_function,
            "flash_loan_callback": flash_loan_callback,
            "flash_loan_validation": flash_loan_validation,
            "flash_loan_initiator_checked": flash_loan_initiator_checked,
            "flash_loan_repayment_checked": flash_loan_repayment_checked,
            "flash_loan_asset_checked": flash_loan_asset_checked,
            "flash_loan_guard": flash_loan_guard,
            "flash_loan_sensitive_operation": flash_loan_sensitive_operation,
            "has_balance_check": has_balance_check,
            "checks_received_amount": checks_received_amount,
            "has_pause_check": has_pause_check,
            "uses_allowance_adjust": uses_allowance_adjust,
            "has_loops": loop_summary["has_loops"],
            "loop_count": loop_summary["loop_count"],
            "max_loop_depth": loop_summary["max_loop_depth"],
            "has_nested_loop": has_nested_loop,
            "loop_bound_sources": loop_summary["loop_bound_sources"],
            "has_unbounded_loop": loop_summary["has_unbounded_loop"],
            "has_require_bounds": has_require_bounds,
            "external_calls_in_loop": loop_summary["external_calls_in_loop"],
            "has_delete_in_loop": loop_summary["has_delete_in_loop"],
            "has_unbounded_deletion": loop_summary["has_unbounded_deletion"],
            "uses_transfer": uses_transfer,
            "uses_send": uses_send,
            "transfers_eth": transfers_eth,
            "has_strict_equality_check": has_strict_equality_check,
            "state_write_before_external_call": call_order.get("write_before_call"),
            "state_write_after_external_call": call_order.get("write_after_call"),
            "reads_balance_state": reads_balance_state,
            "writes_balance_state": writes_balance_state,
            "reads_share_state": reads_share_state,
            "writes_share_state": writes_share_state,
            "reads_supply_state": reads_supply_state,
            "writes_supply_state": writes_supply_state,
            "semgrep_like_rules": sorted(semgrep_rules),
            "semgrep_like_count": len(semgrep_rules),
            "semgrep_like_security_count": semgrep_security_count,
            # Semantic operations
            "semantic_ops": semantic_op_names,
            "op_sequence": op_sequence,
            "behavioral_signature": behavioral_signature,
            "op_ordering": op_ordering,
            # Source location
            "file": file_path,
            "line_start": line_start,
            "line_end": line_end,
            # Contract context properties
            "contract_has_timelock": contract_has_timelock,
            "contract_has_multisig": contract_has_multisig,
            "contract_has_governance": contract_has_governance,
            "contract_has_beacon_state": contract_has_beacon_state,
            "contract_has_withdraw": contract_has_withdraw,
            "contract_has_emergency_withdraw": contract_has_emergency_withdraw,
            "contract_has_emergency_pause": contract_has_emergency_pause,
            "contract_is_upgradeable": contract_is_upgradeable,
            "contract_is_uups_proxy": contract_is_uups_proxy,
            "contract_is_beacon_proxy": contract_is_beacon_proxy,
            "contract_is_diamond_proxy": contract_is_diamond_proxy,
            "contract_is_implementation_contract": contract_is_implementation_contract,
            "compiler_version_lt_08": compiler_version_lt_08,
            "contract_has_inheritance": contract_has_inheritance,
            "contract_has_composition": contract_has_composition,
            "contract_has_balance_tracking": contract_has_balance_tracking,
            # =========================================================
            # Properties previously missing from emission (Phase 2.1)
            # =========================================================
            # Arithmetic & precision
            "uses_arithmetic": uses_arithmetic,
            "uses_division": uses_division,
            "uses_unchecked_block": uses_unchecked_block,
            "has_unchecked_block": has_unchecked_block,
            "has_arithmetic": has_arithmetic,
            "has_division": has_division,
            "has_multiplication": has_multiplication,
            "division_before_multiplication": division_before_multiplication,
            "divisor_source": divisor_source,
            "divisor_validated_nonzero": divisor_validated_nonzero,
            "has_precision_guard": has_precision_guard,
            "has_rounding_ops": has_rounding_ops,
            "large_number_multiplication": large_number_multiplication,
            "price_amount_multiplication": price_amount_multiplication,
            "percentage_calculation": percentage_calculation,
            "percentage_bounds_check": percentage_bounds_check,
            "basis_points_calculation": basis_points_calculation,
            "ratio_calculation": ratio_calculation,
            "fee_calculation": fee_calculation,
            "fee_accumulation": fee_accumulation,
            "timestamp_arithmetic": timestamp_arithmetic,
            "uses_token_decimals": uses_token_decimals,
            "decimal_scaling_usage": decimal_scaling_usage,
            "uses_safemath": uses_safemath,
            "uses_muldiv_or_safemath": uses_muldiv_or_safemath,
            "unchecked_contains_arithmetic": unchecked_contains_arithmetic,
            "unchecked_operand_from_user": unchecked_operand_from_user,
            "unchecked_affects_balance": unchecked_affects_balance,
            # Parameter classification
            "has_bytes_or_string_parameter": has_bytes_or_string_parameter,
            "has_bytes_length_check": has_bytes_length_check,
            "has_fee_parameter": has_fee_parameter,
            "has_fee_bounds": has_fee_bounds,
            "has_duration_parameter": has_duration_parameter,
            "has_duration_bounds": has_duration_bounds,
            "has_minimum_output_parameter": has_minimum_output_parameter,
            "has_minimum_output": has_minimum_output,
            # Oracle extended
            "oracle_call_count": oracle_call_count,
            "oracle_source_count": oracle_source_count,
            "oracle_source_targets": oracle_source_targets,
            "has_multi_source_oracle": has_multi_source_oracle,
            "validates_started_at_recent": validates_started_at_recent,
            # Loop properties
            "event_emission_in_loop": event_emission_in_loop,
            "mapping_iteration_in_loop": mapping_iteration_in_loop,
            # Reentrancy surface
            "callback_chain_surface": callback_chain_surface,
            "protocol_callback_chain_surface": protocol_callback_chain_surface,
            "callback_entrypoint_surface": callback_entrypoint_surface,
            "token_callback_surface": token_callback_surface,
            # Function classification
            "has_access_modifier": has_access_modifier,
            "is_privileged_operation": is_privileged_operation,
            "is_value_transfer": is_value_transfer,
            "is_pure": is_pure,
            # Derived / bridged properties (Phase 2.2)
            "is_upgradeable": contract_is_upgradeable,
            "has_timelock": contract_has_timelock,
            "has_multisig": contract_has_multisig,
            "has_governance": contract_has_governance,
            "has_privileged_operations": bool(contract_node.properties.get("has_privileged_operations")),
            "calls_external_contract": calls_external_contract,
            "is_implementation_contract": contract_is_implementation_contract,
            # MEV risk composite properties (Phase 2.2)
            "risk_missing_slippage_parameter": bool(swap_like and not has_slippage_parameter),
            "risk_missing_slippage_check": bool(swap_like and not has_slippage_check),
            "risk_missing_deadline_parameter": bool(swap_like and not has_deadline_parameter),
            "risk_missing_deadline_check": bool(swap_like and not has_deadline_check),
        }

        return props


def process_functions(
    ctx: "BuildContext",
    contract: Any,
    contract_node: Node,
) -> list[Node]:
    """Convenience function to process all functions for a contract.

    Args:
        ctx: Build context.
        contract: Slither contract object.
        contract_node: The contract's Node in the graph.

    Returns:
        List of function nodes created.
    """
    processor = FunctionProcessor(ctx)
    return processor.process_all(contract, contract_node)


__all__ = [
    "FunctionProperties",
    "FunctionProcessor",
    "process_functions",
]
