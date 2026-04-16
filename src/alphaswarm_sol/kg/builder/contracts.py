"""Contract-level processing for VKG builder.

This module handles contract node creation and property computation,
extracting logic from the legacy builder into a modular, testable form.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from alphaswarm_sol.kg.heuristics import classify_state_var_name, is_privileged_state
from alphaswarm_sol.kg.schema import Edge, Evidence, KnowledgeGraph, Node
from alphaswarm_sol.kg.semgrep_compat import (
    ContractContext,
    detect_semgrep_contract_rules,
    has_bidi_chars,
)
from alphaswarm_sol.kg.builder.context import BuildContext


@dataclass
class ContractProperties:
    """Computed properties for a contract node.

    All security-relevant properties derived from static analysis
    of a Solidity contract.
    """

    kind: str  # contract, interface, library
    is_proxy_like: bool
    proxy_type: str  # none, uups, transparent, beacon, generic
    has_initializer: bool
    has_upgrade: bool
    has_storage_gap: bool
    storage_gap_sizes: list[int] = field(default_factory=list)
    upgradeable_without_storage_gap: bool = False
    is_upgradeable: bool = False
    is_uups_proxy: bool = False
    is_beacon_proxy: bool = False
    is_diamond_proxy: bool = False
    is_implementation_contract: bool = False
    has_constructor: bool = False
    initializers_disabled: bool = False
    has_selfdestruct: bool = False
    storage_layout_changed: bool = False
    new_variables_not_at_end: bool = False
    inherited_storage_conflict: bool = False
    diamond_storage_isolation: bool = False
    uses_libdiamond: bool = False
    contract_has_beacon_state: bool = False
    contract_has_diamond_cut: bool = False
    owner_is_single_address: bool = False
    owner_uninitialized: bool = False
    has_timelock: bool = False
    has_multisig: bool = False
    has_role_grant: bool = False
    has_role_revoke: bool = False
    has_default_admin_role: bool = False
    has_role_events: bool = False
    default_admin_address_is_zero: bool = False
    has_role_enumeration: bool = False
    has_governance: bool = False
    has_withdraw: bool = False
    has_emergency_withdraw: bool = False
    has_emergency_pause: bool = False
    multisig_threshold_is_one: bool = False
    multisig_threshold_is_zero: bool = False
    timelock_delay_zero: bool = False
    has_oracle_state: bool = False
    has_oracle_feed_setter: bool = False
    has_inheritance: bool = False
    has_composition: bool = False
    has_diamond_inheritance: bool = False
    shadows_parent_variable: bool = False
    compiler_version_lt_08: bool = False
    uses_safemath: bool = False
    has_uninitialized_storage: bool = False
    has_uninitialized_boolean: bool = False
    has_privileged_operations: bool = False
    has_unprotected_privileged_writes: bool = False
    has_protected_privileged_writes: bool = False
    has_inconsistent_access_control: bool = False
    state_var_count: int = 0
    inherits_erc2771: bool = False
    has_multicall: bool = False
    has_bidi_chars: bool = False
    semgrep_like_rules: list[str] = field(default_factory=list)


class ContractProcessor:
    """Process contracts and create contract nodes.

    This class extracts contract-level analysis from the legacy builder,
    using BuildContext for dependency injection and shared state.
    """

    def __init__(self, ctx: BuildContext) -> None:
        """Initialize processor with build context.

        Args:
            ctx: BuildContext for shared state and utilities.
        """
        self.ctx = ctx

    def process(self, contract: Any) -> Node:
        """Process a contract and create its node.

        Args:
            contract: Slither contract object.

        Returns:
            Node representing the contract in the graph.
        """
        file_path, line_start, line_end = self._source_location(contract)
        props = self._compute_properties(contract, file_path, line_start, line_end)

        node_id = self._node_id(props.kind, contract.name, file_path, line_start)
        contract_rules = detect_semgrep_contract_rules(
            ContractContext(
                name=contract.name,
                is_proxy_like=props.is_proxy_like,
                has_storage_gap=props.has_storage_gap,
                state_var_count=props.state_var_count,
                inherits_erc2771=props.inherits_erc2771,
                has_multicall=props.has_multicall,
                has_bidi_chars=props.has_bidi_chars,
            )
        )

        node = Node(
            id=node_id,
            type="Contract",
            label=contract.name,
            properties={
                "kind": props.kind,
                "has_initializer": props.has_initializer,
                "has_upgrade_function": props.has_upgrade,
                "is_proxy_like": props.is_proxy_like,
                "proxy_type": props.proxy_type,
                "has_storage_gap": props.has_storage_gap,
                "storage_gap_sizes": props.storage_gap_sizes,
                "upgradeable_without_storage_gap": props.upgradeable_without_storage_gap,
                "is_upgradeable": props.is_upgradeable,
                "is_uups_proxy": props.is_uups_proxy,
                "is_beacon_proxy": props.is_beacon_proxy,
                "is_diamond_proxy": props.is_diamond_proxy,
                "is_implementation_contract": props.is_implementation_contract,
                "has_constructor": props.has_constructor,
                "initializers_disabled": props.initializers_disabled,
                "has_selfdestruct": props.has_selfdestruct,
                "storage_layout_changed": props.storage_layout_changed,
                "new_variables_not_at_end": props.new_variables_not_at_end,
                "inherited_storage_conflict": props.inherited_storage_conflict,
                "diamond_storage_isolation": props.diamond_storage_isolation,
                "uses_libdiamond": props.uses_libdiamond,
                "contract_has_beacon_state": props.contract_has_beacon_state,
                "contract_has_diamond_cut": props.contract_has_diamond_cut,
                "owner_is_single_address": props.owner_is_single_address,
                "owner_uninitialized": props.owner_uninitialized,
                "has_timelock": props.has_timelock,
                "has_multisig": props.has_multisig,
                "has_role_grant": props.has_role_grant,
                "has_role_revoke": props.has_role_revoke,
                "has_default_admin_role": props.has_default_admin_role,
                "has_role_events": props.has_role_events,
                "default_admin_address_is_zero": props.default_admin_address_is_zero,
                "has_role_enumeration": props.has_role_enumeration,
                "has_governance": props.has_governance,
                "has_withdraw": props.has_withdraw,
                "has_emergency_withdraw": props.has_emergency_withdraw,
                "has_emergency_pause": props.has_emergency_pause,
                "multisig_threshold_is_one": props.multisig_threshold_is_one,
                "multisig_threshold_is_zero": props.multisig_threshold_is_zero,
                "timelock_delay_zero": props.timelock_delay_zero,
                "has_oracle_state": props.has_oracle_state,
                "has_oracle_feed_setter": props.has_oracle_feed_setter,
                "has_inheritance": props.has_inheritance,
                "has_inherited_contracts": props.has_inheritance,  # Alias for compatibility
                "has_composition": props.has_composition,
                "has_diamond_inheritance": props.has_diamond_inheritance,
                "shadows_parent_variable": props.shadows_parent_variable,
                "compiler_version_lt_08": props.compiler_version_lt_08,
                "uses_safemath": props.uses_safemath,
                "has_uninitialized_storage": props.has_uninitialized_storage,
                "has_uninitialized_boolean": props.has_uninitialized_boolean,
                "has_privileged_operations": props.has_privileged_operations,
                "has_unprotected_privileged_writes": props.has_unprotected_privileged_writes,
                "has_protected_privileged_writes": props.has_protected_privileged_writes,
                "has_inconsistent_access_control": props.has_inconsistent_access_control,
                "state_var_count": props.state_var_count,
                "inherits_erc2771": props.inherits_erc2771,
                "has_multicall": props.has_multicall,
                "has_bidi_chars": props.has_bidi_chars,
                "semgrep_like_rules": sorted(contract_rules),
                "semgrep_like_count": len(contract_rules),
                "file": file_path,
                "line_start": line_start,
                "line_end": line_end,
            },
            evidence=self._evidence(file_path, line_start, line_end),
        )
        return self.ctx.graph.add_node(node)

    def process_inheritance(self, contract: Any, contract_node: Node) -> None:
        """Process contract inheritance and create edges.

        Args:
            contract: Slither contract object.
            contract_node: Node for the contract.
        """
        for base in getattr(contract, "inheritance", []) or []:
            file_path, line_start, line_end = self._source_location(base)
            base_id = self._node_id("contract", base.name, file_path, line_start)
            base_node = Node(
                id=base_id,
                type="Contract",
                label=base.name,
                properties={
                    "kind": "contract",
                    "file": file_path,
                    "line_start": line_start,
                    "line_end": line_end,
                },
                evidence=self._evidence(file_path, line_start, line_end),
            )
            self.ctx.graph.add_node(base_node)
            self.ctx.graph.add_edge(
                Edge(
                    id=self._edge_id("INHERITS", contract_node.id, base_id),
                    type="INHERITS",
                    source=contract_node.id,
                    target=base_id,
                    evidence=self._evidence(
                        contract_node.properties.get("file"), None, None
                    ),
                )
            )

    def _compute_properties(
        self,
        contract: Any,
        file_path: str,
        line_start: int | None,
        line_end: int | None,
    ) -> ContractProperties:
        """Compute all security properties for a contract.

        Args:
            contract: Slither contract object.
            file_path: Path to source file.
            line_start: Start line number.
            line_end: End line number.

        Returns:
            ContractProperties with all computed values.
        """
        # Determine kind
        kind = "contract"
        if getattr(contract, "is_interface", False):
            kind = "interface"
        elif getattr(contract, "is_library", False):
            kind = "library"

        # Extract function and state variable names
        function_names = [
            fn.name for fn in getattr(contract, "functions", []) if getattr(fn, "name", None)
        ]
        lowered_function_names = [name.lower() for name in function_names]
        state_vars = getattr(contract, "state_variables", []) or []
        state_var_names = [getattr(var, "name", "") or "" for var in state_vars]
        lowered_state_var_names = [name.lower() for name in state_var_names if name]

        # Basic upgrade/proxy detection
        has_initializer = any("initialize" in name for name in lowered_function_names)
        has_upgrade = any(name.startswith("upgrade") for name in lowered_function_names)
        is_proxy_like = (
            "proxy" in contract.name.lower() or "upgradeable" in contract.name.lower()
        )
        proxy_type = self._detect_proxy_type(contract)
        has_storage_gap, storage_gap_sizes = self._storage_gap_info(contract)
        upgradeable_without_storage_gap = (has_upgrade or is_proxy_like) and not has_storage_gap

        # Ownership and access control
        owner_is_single_address = self._owner_is_single_address(state_vars)
        owner_uninitialized = self._owner_uninitialized(state_vars)

        # Timelock detection
        has_timelock = any(
            "timelock" in name or "time_lock" in name for name in lowered_state_var_names
        )
        has_timelock = has_timelock or any("timelock" in name for name in lowered_function_names)

        # Multisig detection
        has_multisig = "multisig" in contract.name.lower()
        has_multisig = has_multisig or any(
            token in name
            for token in ("multisig", "multi_sig", "threshold", "signer", "signers", "owners")
            for name in lowered_state_var_names
        )
        has_multisig = has_multisig or any(
            token in name
            for token in ("multisig", "threshold", "signer", "signers")
            for name in lowered_function_names
        )

        # Role management detection
        has_role_grant = any(
            token in name
            for token in ("grant", "addrole", "setrole", "assignrole")
            for name in lowered_function_names
        )
        has_role_revoke = any(
            token in name
            for token in ("revoke", "removerole", "revokerole")
            for name in lowered_function_names
        )
        has_default_admin_role = any(
            token in name
            for token in (
                "default_admin",
                "defaultadmin",
                "default_admin_role",
                "defaultadminrole",
            )
            for name in lowered_state_var_names
        )
        has_role_events = self._has_role_events(contract)
        default_admin_address_is_zero = self._default_admin_address_is_zero(state_vars)
        has_role_enumeration = self._has_role_enumeration(state_vars)
        has_governance = self._has_governance_signals(state_vars, lowered_function_names)
        multisig_threshold_is_one = self._multisig_threshold_is_one(state_vars)
        multisig_threshold_is_zero = self._multisig_threshold_is_zero(state_vars)
        timelock_delay_zero = self._timelock_delay_zero(state_vars)
        privileged_summary = self._summarize_contract_privilege(contract)

        # Oracle detection
        has_oracle_state = any(
            token in name
            for token in ("oracle", "pricefeed", "aggregator")
            for name in lowered_state_var_names
        )
        has_oracle_feed_setter = any(
            token in name
            for token in (
                "setoracle",
                "setpricefeed",
                "setfeed",
                "setaggregator",
                "setchainlink",
            )
            for name in lowered_function_names
        )

        # Inheritance and composition
        has_inheritance = bool(getattr(contract, "inheritance", []) or [])
        has_composition = self._contract_has_composition(contract)
        inherits_erc2771 = any(
            "erc2771" in base.name.lower()
            for base in getattr(contract, "inheritance", []) or []
            if getattr(base, "name", None)
        )
        has_multicall = any("multicall" in name for name in lowered_function_names)

        # Source text analysis
        file_text = ""
        if file_path and file_path != "unknown":
            file_text = "\n".join(self.ctx.get_source_lines(file_path))
        file_text_lower = file_text.lower()
        contract_source_text = self._source_slice(file_path, line_start, line_end).lower()
        contract_source_clean = self._strip_comments(contract_source_text)

        bidi_present = has_bidi_chars(file_text)
        compiler_version_lt_08 = self._is_pre_08_pragma(file_text)
        uses_safemath = self._uses_safemath(file_text)
        has_uninitialized_storage = self._has_uninitialized_storage_var(state_vars)
        has_uninitialized_boolean = self._has_uninitialized_bool_var(state_vars)
        has_diamond_inheritance = self._has_diamond_inheritance(contract)
        shadows_parent_variable = self._has_shadowing(contract)

        # Implementation contract detection
        is_implementation_contract = (not is_proxy_like) and (
            has_upgrade
            or "implementation" in contract.name.lower()
            or "logic" in contract.name.lower()
        )

        # Enhanced semantic detection for upgradeability
        inherits_upgradeable_base = self._inherits_upgradeable_base(contract)
        has_upgrade_pattern = self._has_upgrade_pattern(function_names)
        is_upgradeable = bool(
            has_upgrade
            or is_proxy_like
            or is_implementation_contract
            or inherits_upgradeable_base
            or has_upgrade_pattern
        )
        is_uups_proxy = proxy_type == "uups"
        is_beacon_proxy = proxy_type == "beacon"
        is_diamond_proxy = "diamond" in contract.name.lower() or any(
            "diamond" in base.name.lower()
            for base in getattr(contract, "inheritance", []) or []
            if getattr(base, "name", None)
        )

        # Constructor and initializer analysis
        constructor_present = "constructor" in contract_source_clean
        initializers_disabled = (
            "_disableinitializers" in contract_source_clean
            or "disableinitializers" in contract_source_clean
        )
        if not initializers_disabled and constructor_present:
            if re.search(
                r"\b_initialized\s*=\s*type\s*\(\s*uint8\s*\)\s*\.max",
                contract_source_clean,
            ):
                initializers_disabled = True
            elif re.search(r"\b_initialized\s*=\s*1\b", contract_source_clean):
                initializers_disabled = True
            elif re.search(r"\b_initialized\s*=\s*true\b", contract_source_clean):
                initializers_disabled = True
            elif re.search(r"\binitialized\s*=\s*true\b", contract_source_clean):
                initializers_disabled = True

        contract_has_selfdestruct = (
            "selfdestruct" in contract_source_clean or "suicide" in contract_source_clean
        )

        # Storage layout analysis
        gap_indices = [
            idx for idx, name in enumerate(state_var_names) if "gap" in name.lower()
        ]
        new_variables_not_at_end = False
        if gap_indices:
            last_gap = max(gap_indices)
            for idx in range(last_gap + 1, len(state_var_names)):
                if "gap" not in state_var_names[idx].lower():
                    new_variables_not_at_end = True
                    break

        storage_layout_changed = bool(is_implementation_contract and not has_storage_gap)
        inherited_storage_conflict = bool(
            has_inheritance and is_implementation_contract and not has_storage_gap
        )
        diamond_storage_isolation = any(
            token in contract_source_clean
            for token in ("diamondstorage", "libdiamond", "appstorage", "diamond.storage")
        )
        contract_has_beacon_state = any("beacon" in name.lower() for name in state_var_names)
        uses_libdiamond = diamond_storage_isolation

        contract_has_diamond_cut = any(
            "diamondcut" in name or "facetcut" in name for name in lowered_function_names
        )
        contract_has_withdraw = any(
            any(token in name for token in ("withdraw", "claim", "redeem", "release"))
            for name in lowered_function_names
        )
        contract_has_emergency_withdraw = any(
            "emergency" in name
            and any(token in name for token in ("withdraw", "rescue", "recover"))
            for name in lowered_function_names
        )
        contract_has_emergency_pause = any("pause" in name for name in lowered_function_names)

        return ContractProperties(
            kind=kind,
            is_proxy_like=is_proxy_like,
            proxy_type=proxy_type,
            has_initializer=has_initializer,
            has_upgrade=has_upgrade,
            has_storage_gap=has_storage_gap,
            storage_gap_sizes=storage_gap_sizes,
            upgradeable_without_storage_gap=upgradeable_without_storage_gap,
            is_upgradeable=is_upgradeable,
            is_uups_proxy=is_uups_proxy,
            is_beacon_proxy=is_beacon_proxy,
            is_diamond_proxy=is_diamond_proxy,
            is_implementation_contract=is_implementation_contract,
            has_constructor=constructor_present,
            initializers_disabled=initializers_disabled,
            has_selfdestruct=contract_has_selfdestruct,
            storage_layout_changed=storage_layout_changed,
            new_variables_not_at_end=new_variables_not_at_end,
            inherited_storage_conflict=inherited_storage_conflict,
            diamond_storage_isolation=diamond_storage_isolation,
            uses_libdiamond=uses_libdiamond,
            contract_has_beacon_state=contract_has_beacon_state,
            contract_has_diamond_cut=contract_has_diamond_cut,
            owner_is_single_address=owner_is_single_address,
            owner_uninitialized=owner_uninitialized,
            has_timelock=has_timelock,
            has_multisig=has_multisig,
            has_role_grant=has_role_grant,
            has_role_revoke=has_role_revoke,
            has_default_admin_role=has_default_admin_role,
            has_role_events=has_role_events,
            default_admin_address_is_zero=default_admin_address_is_zero,
            has_role_enumeration=has_role_enumeration,
            has_governance=has_governance,
            has_withdraw=contract_has_withdraw,
            has_emergency_withdraw=contract_has_emergency_withdraw,
            has_emergency_pause=contract_has_emergency_pause,
            multisig_threshold_is_one=multisig_threshold_is_one,
            multisig_threshold_is_zero=multisig_threshold_is_zero,
            timelock_delay_zero=timelock_delay_zero,
            has_oracle_state=has_oracle_state,
            has_oracle_feed_setter=has_oracle_feed_setter,
            has_inheritance=has_inheritance,
            has_composition=has_composition,
            has_diamond_inheritance=has_diamond_inheritance,
            shadows_parent_variable=shadows_parent_variable,
            compiler_version_lt_08=compiler_version_lt_08,
            uses_safemath=uses_safemath,
            has_uninitialized_storage=has_uninitialized_storage,
            has_uninitialized_boolean=has_uninitialized_boolean,
            has_privileged_operations=privileged_summary["has_privileged_operations"],
            has_unprotected_privileged_writes=privileged_summary[
                "has_unprotected_privileged_writes"
            ],
            has_protected_privileged_writes=privileged_summary[
                "has_protected_privileged_writes"
            ],
            has_inconsistent_access_control=privileged_summary[
                "has_inconsistent_access_control"
            ],
            state_var_count=len(state_vars),
            inherits_erc2771=inherits_erc2771,
            has_multicall=has_multicall,
            has_bidi_chars=bidi_present,
        )

    # =========================================================================
    # Proxy Detection Methods
    # =========================================================================

    def _detect_proxy_type(self, contract: Any) -> str:
        """Detect proxy type from contract structure.

        Args:
            contract: Slither contract object.

        Returns:
            Proxy type string: none, uups, transparent, beacon, generic.
        """
        name = (getattr(contract, "name", "") or "").lower()
        base_names = [
            base.name.lower()
            for base in getattr(contract, "inheritance", []) or []
            if getattr(base, "name", None)
        ]
        fn_names = [
            fn.name.lower()
            for fn in getattr(contract, "functions", []) or []
            if getattr(fn, "name", None)
        ]
        state_names = [
            var.name.lower()
            for var in getattr(contract, "state_variables", []) or []
            if getattr(var, "name", None)
        ]

        if any("beacon" in token for token in [name] + base_names + fn_names + state_names):
            return "beacon"
        if "transparent" in name or any("transparent" in base for base in base_names):
            return "transparent"
        if "uups" in name or any("uups" in base for base in base_names):
            return "uups"
        if "admin" in fn_names and "implementation" in fn_names:
            return "transparent"
        if any(fn in fn_names for fn in ("upgradeto", "upgradetoandcall")):
            return "uups"
        if "proxy" in name or "proxy" in " ".join(base_names):
            return "generic"
        return "none"

    def _storage_gap_info(self, contract: Any) -> tuple[bool, list[int]]:
        """Check for storage gap variables and their sizes.

        Args:
            contract: Slither contract object.

        Returns:
            Tuple of (has_gap, list of gap sizes).
        """
        sizes: list[int] = []
        for var in getattr(contract, "state_variables", []) or []:
            name = getattr(var, "name", None) or ""
            if "gap" not in name.lower():
                continue
            var_type = getattr(var, "type", None)
            type_name = str(var_type) if var_type is not None else ""
            match = re.search(r"\[(\d+)\]", type_name)
            if match:
                sizes.append(int(match.group(1)))
        return bool(sizes), sorted(set(sizes))

    def _is_upgrade_function(self, fn: Any) -> bool:
        """Check if function is an upgrade function.

        Args:
            fn: Slither function object.

        Returns:
            True if this is an upgrade function.
        """
        name = (getattr(fn, "name", "") or "").lower()
        signature = getattr(fn, "signature", "") or ""
        if isinstance(signature, (list, tuple)):
            signature_text = " ".join(str(item) for item in signature)
        else:
            signature_text = str(signature)
        signature_text = signature_text.lower()
        tokens = ("upgrade", "setimplementation", "setbeacon", "upgradebeacon")
        return any(token in name for token in tokens) or any(
            token in signature_text for token in tokens
        )

    def _inherits_upgradeable_base(self, contract: Any) -> bool:
        """Detect if contract inherits from common upgradeable base contracts.

        Args:
            contract: Slither contract object.

        Returns:
            True if inherits from upgradeable base.
        """
        upgradeable_base_patterns = [
            "initializable",
            "uupsupgradeable",
            "upgradeable",
            "transparentupgradeable",
            "beaconupgradeable",
            "upgradeableproxy",
            "proxyupgradeable",
        ]

        bases = getattr(contract, "inheritance", []) or []
        for base in bases:
            base_name = getattr(base, "name", "").lower()
            if any(pattern in base_name for pattern in upgradeable_base_patterns):
                return True
        return False

    def _has_upgrade_pattern(self, function_names: list[str]) -> bool:
        """Detect specific upgrade function patterns.

        Args:
            function_names: List of function names.

        Returns:
            True if upgrade pattern detected.
        """
        upgrade_function_patterns = [
            "upgradetoandcall",
            "_authorizeupgrade",
            "upgradeto",
            "upgradeandcall",
            "setimplementation",
            "_upgradeimplementation",
            "upgradebeacon",
        ]

        lowered_names = [name.lower() for name in function_names]
        return any(
            pattern in name or name == pattern
            for pattern in upgrade_function_patterns
            for name in lowered_names
        )

    # =========================================================================
    # Ownership and Access Control Methods
    # =========================================================================

    def _owner_is_single_address(self, state_vars: list[Any]) -> bool:
        """Check if owner is a single address (not mapping/array).

        Args:
            state_vars: List of state variables.

        Returns:
            True if owner is single address.
        """
        for var in state_vars:
            name = getattr(var, "name", None)
            if not name:
                continue
            tags = classify_state_var_name(name)
            if "owner" not in tags:
                continue
            var_type = getattr(var, "type", None)
            type_name = str(var_type).lower() if var_type is not None else ""
            if "mapping" in type_name or "[" in type_name:
                continue
            if "address" in type_name:
                return True
        return False

    def _owner_uninitialized(self, state_vars: list[Any]) -> bool:
        """Check if owner variable is uninitialized.

        Args:
            state_vars: List of state variables.

        Returns:
            True if owner is uninitialized.
        """
        for var in state_vars:
            name = getattr(var, "name", None)
            if not name:
                continue
            tags = classify_state_var_name(name)
            if "owner" not in tags:
                continue
            expression = getattr(var, "expression", None) or getattr(var, "value", None)
            if expression is None:
                return True
        return False

    def _default_admin_address_is_zero(self, state_vars: list[Any]) -> bool:
        """Check if default admin address is zero.

        Args:
            state_vars: List of state variables.

        Returns:
            True if default admin is address(0).
        """
        for var in state_vars:
            name = (getattr(var, "name", "") or "").lower()
            if "default_admin" not in name and "defaultadmin" not in name:
                continue
            var_type = getattr(var, "type", None)
            type_name = str(var_type).lower() if var_type is not None else ""
            if "address" not in type_name:
                continue
            expression = getattr(var, "expression", None) or getattr(var, "value", None)
            if expression is None:
                continue
            text = str(expression).strip().lower()
            if text in {
                "address(0)",
                "0x0",
                "0x0000000000000000000000000000000000000000",
                "0",
            }:
                return True
        return False

    def _has_role_enumeration(self, state_vars: list[Any]) -> bool:
        """Check for role enumeration patterns.

        Args:
            state_vars: List of state variables.

        Returns:
            True if role enumeration detected.
        """
        for var in state_vars:
            name = (getattr(var, "name", "") or "").lower()
            if not name:
                continue
            if any(
                token in name
                for token in (
                    "member",
                    "members",
                    "enumerable",
                    "rolelist",
                    "role_list",
                    "roleset",
                )
            ):
                return True
        return False

    def _has_role_events(self, contract: Any) -> bool:
        """Check for role-related events.

        Args:
            contract: Slither contract object.

        Returns:
            True if role events found.
        """
        for event in getattr(contract, "events", []) or []:
            name = (getattr(event, "name", "") or "").lower()
            if any(token in name for token in ("role", "grant", "revoke", "admin")):
                return True
        return False

    def _has_governance_signals(
        self, state_vars: list[Any], function_names: list[str]
    ) -> bool:
        """Check for governance-related patterns.

        Args:
            state_vars: List of state variables.
            function_names: List of function names.

        Returns:
            True if governance signals detected.
        """
        tokens = ("govern", "governor", "council", "quorum", "proposal", "vote", "timelock")
        for var in state_vars:
            name = (getattr(var, "name", "") or "").lower()
            if any(token in name for token in tokens):
                return True
        for name in function_names:
            if any(token in name for token in tokens):
                return True
        return False

    def _multisig_threshold_is_one(self, state_vars: list[Any]) -> bool:
        """Check if multisig threshold is set to 1.

        Args:
            state_vars: List of state variables.

        Returns:
            True if threshold is 1.
        """
        for var in state_vars:
            name = (getattr(var, "name", "") or "").lower()
            if "threshold" not in name:
                continue
            expression = getattr(var, "expression", None) or getattr(var, "value", None)
            if expression is None:
                continue
            text = str(expression).strip()
            if re.fullmatch(r"1(\.0+)?", text):
                return True
        return False

    def _multisig_threshold_is_zero(self, state_vars: list[Any]) -> bool:
        """Check if multisig threshold is set to 0.

        Args:
            state_vars: List of state variables.

        Returns:
            True if threshold is 0.
        """
        for var in state_vars:
            name = (getattr(var, "name", "") or "").lower()
            if "threshold" not in name:
                continue
            expression = getattr(var, "expression", None) or getattr(var, "value", None)
            if expression is None:
                continue
            text = str(expression).strip()
            if re.fullmatch(r"0(\.0+)?", text):
                return True
        return False

    def _timelock_delay_zero(self, state_vars: list[Any]) -> bool:
        """Check if timelock delay is set to 0.

        Args:
            state_vars: List of state variables.

        Returns:
            True if timelock delay is 0.
        """
        for var in state_vars:
            name = (getattr(var, "name", "") or "").lower()
            if not any(token in name for token in ("timelock", "delay", "cooldown", "eta")):
                continue
            expression = getattr(var, "expression", None) or getattr(var, "value", None)
            if expression is None:
                continue
            text = str(expression).strip()
            if re.fullmatch(r"0(\.0+)?", text):
                return True
        return False

    def _summarize_contract_privilege(self, contract: Any) -> dict[str, bool]:
        """Summarize privileged operations in contract.

        Args:
            contract: Slither contract object.

        Returns:
            Dictionary with privilege summary flags.
        """
        has_unprotected = False
        has_protected = False
        has_privileged = False

        for fn in getattr(contract, "functions", []) or []:
            modifiers = [
                m.name for m in getattr(fn, "modifiers", []) if getattr(m, "name", None)
            ]
            access_gate_mods = [m for m in modifiers if self._is_access_gate(m)]
            access_gate_logic, _ = self._access_gate_from_predicates(fn)
            has_access_gate = bool(access_gate_mods) or access_gate_logic

            writes_state = getattr(fn, "state_variables_written", []) or []
            state_write_targets = self._classify_state_write_targets(writes_state)
            writes_privileged_state = any(
                is_privileged_state(tags) for tags in state_write_targets.values()
            )

            uses_transfer = self._uses_transfer(fn)
            uses_send = self._uses_send(fn)

            low_level_calls = getattr(fn, "low_level_calls", []) or []
            low_level_names = []
            for call in low_level_calls:
                for attr in ("name", "function_name", "full_name"):
                    name = getattr(call, attr, None)
                    if name:
                        low_level_names.append(str(name))
            low_level_names = [name for name in low_level_names if name]
            uses_call = any(name.lower() in {"call", "staticcall"} for name in low_level_names)

            if writes_privileged_state or uses_transfer or uses_send or uses_call:
                has_privileged = True
            if writes_privileged_state and has_access_gate:
                has_protected = True
            if writes_privileged_state and not has_access_gate:
                has_unprotected = True

        return {
            "has_privileged_operations": has_privileged,
            "has_unprotected_privileged_writes": has_unprotected,
            "has_protected_privileged_writes": has_protected,
            "has_inconsistent_access_control": bool(has_protected and has_unprotected),
        }

    def _is_access_gate(self, modifier_name: str) -> bool:
        """Check if modifier is an access gate.

        Args:
            modifier_name: Name of the modifier.

        Returns:
            True if this is an access gate modifier.
        """
        lowered = modifier_name.lower()
        keywords = ("only", "auth", "role", "admin", "owner", "guardian", "governor")
        return any(key in lowered for key in keywords)

    def _access_gate_from_predicates(self, fn: Any) -> tuple[bool, list[str]]:
        """Detect access gates from require/assert predicates.

        Args:
            fn: Slither function object.

        Returns:
            Tuple of (has_gate, list of gate sources).
        """
        sources: set[str] = set()
        for expression in self._require_expressions(fn):
            if "msg.sender" in expression:
                sources.add("msg.sender")
            if "tx.origin" in expression:
                sources.add("tx.origin")
            if "[msg.sender]" in expression or "msg.sender]" in expression:
                sources.add("mapping[msg.sender]")
            if "msg.value" in expression:
                sources.add("msg.value")
            if "block.timestamp" in expression:
                sources.add("block.timestamp")
            if "block.number" in expression:
                sources.add("block.number")
            if "block.chainid" in expression:
                sources.add("block.chainid")
            if "blockhash" in expression:
                sources.add("blockhash")
            if "block.prevrandao" in expression:
                sources.add("block.prevrandao")
        return (bool(sources), sorted(sources))

    def _require_expressions(self, fn: Any) -> list[str]:
        """Extract require/assert expressions from function.

        Args:
            fn: Slither function object.

        Returns:
            List of require/assert expression strings.
        """
        expressions: list[str] = []
        for node in getattr(fn, "nodes", []) or []:
            for ir in getattr(node, "irs", []) or []:
                if type(ir).__name__ != "SolidityCall":
                    continue
                expression = str(getattr(ir, "expression", "")) or str(ir)
                if "require" in expression or "assert" in expression:
                    expressions.append(expression)
        return expressions

    def _classify_state_write_targets(self, state_vars: list[Any]) -> dict[str, list[str]]:
        """Classify state variables by their security tags.

        Args:
            state_vars: List of state variables.

        Returns:
            Dictionary mapping var names to security tags.
        """
        targets: dict[str, list[str]] = {}
        for var in state_vars:
            name = getattr(var, "name", None) or ""
            if not name:
                continue
            tags = classify_state_var_name(name)
            targets[name] = tags
        return targets

    def _uses_transfer(self, fn: Any) -> bool:
        """Detect usage of .transfer() method.

        Args:
            fn: Slither function object.

        Returns:
            True if .transfer() is used.
        """
        for node in getattr(fn, "nodes", []) or []:
            expression = self._node_expression(node)
            if ".transfer(" in expression:
                return True
            for ir in getattr(node, "irs", []) or []:
                ir_str = str(ir).lower()
                if "transfer(" in ir_str:
                    return True
        return False

    def _uses_send(self, fn: Any) -> bool:
        """Detect usage of .send() method.

        Args:
            fn: Slither function object.

        Returns:
            True if .send() is used.
        """
        for node in getattr(fn, "nodes", []) or []:
            expression = self._node_expression(node)
            if ".send(" in expression:
                return True
            for ir in getattr(node, "irs", []) or []:
                ir_str = str(ir).lower()
                if "send(" in ir_str:
                    return True
        return False

    def _node_expression(self, node: Any) -> str:
        """Get expression string from a CFG node.

        Args:
            node: Slither CFG node.

        Returns:
            Expression as string.
        """
        expression = getattr(node, "expression", None)
        if expression is None:
            return ""
        return str(expression)

    # =========================================================================
    # Contract Structure Methods
    # =========================================================================

    def _contract_has_composition(self, contract: Any) -> bool:
        """Check if contract uses composition pattern.

        Args:
            contract: Slither contract object.

        Returns:
            True if composition detected.
        """
        for var in getattr(contract, "state_variables", []) or []:
            tags = classify_state_var_name(getattr(var, "name", "") or "")
            if "dependency" in tags:
                return True
        return False

    def _has_diamond_inheritance(self, contract: Any) -> bool:
        """Check for diamond inheritance pattern.

        Args:
            contract: Slither contract object.

        Returns:
            True if diamond inheritance detected.
        """
        bases = getattr(contract, "inheritance", []) or []
        if len(bases) < 2:
            return False
        for base in bases:
            if getattr(base, "inheritance", []) or []:
                return True
        return True

    def _has_shadowing(self, contract: Any) -> bool:
        """Check for variable shadowing.

        Args:
            contract: Slither contract object.

        Returns:
            True if shadowing detected.
        """
        state_vars = {
            getattr(var, "name", None)
            for var in getattr(contract, "state_variables", []) or []
        }
        state_vars.discard(None)
        if not state_vars:
            return False

        for fn in getattr(contract, "functions", []) or []:
            parameters = [
                getattr(p, "name", None) for p in getattr(fn, "parameters", []) or []
            ]
            locals_ = [
                getattr(v, "name", None) for v in getattr(fn, "local_variables", []) or []
            ]
            locals_ += [
                getattr(v, "name", None) for v in getattr(fn, "variables", []) or []
            ]
            for name in parameters + locals_:
                if name and name in state_vars:
                    return True
        return False

    # =========================================================================
    # Source Analysis Methods
    # =========================================================================

    def _is_pre_08_pragma(self, file_text: str) -> bool:
        """Check if pragma specifies pre-0.8 Solidity.

        Args:
            file_text: Full source file text.

        Returns:
            True if pre-0.8 Solidity.
        """
        if not file_text:
            return False
        match = re.search(r"pragma\s+solidity\s+([^;]+);", file_text)
        if not match:
            return False
        pragma = match.group(1).strip()
        version_tokens = re.findall(r"([<>=^~]*)\s*(0\.\d+(?:\.\d+)?)", pragma)
        if not version_tokens:
            return False
        has_ge_08 = any(
            cmp in (">=", ">", "^", "~") and ver.startswith("0.8")
            for cmp, ver in version_tokens
        )
        if has_ge_08:
            return False
        has_lt_08 = any(
            cmp.startswith("<") and ver.startswith(("0.7", "0.6", "0.5", "0.4"))
            for cmp, ver in version_tokens
        )
        if has_lt_08:
            return True
        return any(ver.startswith(("0.7", "0.6", "0.5", "0.4")) for _cmp, ver in version_tokens)

    def _uses_safemath(self, file_text: str) -> bool:
        """Check if SafeMath is used.

        Args:
            file_text: Full source file text.

        Returns:
            True if SafeMath is used.
        """
        return "safemath" in file_text.lower()

    def _has_uninitialized_storage_var(self, state_vars: list[Any]) -> bool:
        """Check for uninitialized storage variables.

        Args:
            state_vars: List of state variables.

        Returns:
            True if uninitialized storage variable found.
        """
        for var in state_vars:
            if getattr(var, "is_constant", False) or getattr(var, "is_immutable", False):
                continue
            expression = getattr(var, "expression", None) or getattr(var, "value", None)
            if expression is None:
                return True
        return False

    def _has_uninitialized_bool_var(self, state_vars: list[Any]) -> bool:
        """Check for uninitialized boolean variables.

        Args:
            state_vars: List of state variables.

        Returns:
            True if uninitialized bool found.
        """
        for var in state_vars:
            if getattr(var, "is_constant", False) or getattr(var, "is_immutable", False):
                continue
            var_type = str(getattr(var, "type", "") or "").lower()
            if "bool" not in var_type:
                continue
            expression = getattr(var, "expression", None) or getattr(var, "value", None)
            if expression is None:
                return True
        return False

    def _strip_comments(self, text: str) -> str:
        """Remove comments from source text.

        Args:
            text: Source text.

        Returns:
            Text with comments removed.
        """
        if not text:
            return ""
        no_line = re.sub(r"//.*", "", text)
        return re.sub(r"/\*.*?\*/", "", no_line, flags=re.DOTALL)

    # =========================================================================
    # Utility Methods
    # =========================================================================

    def _source_location(self, obj: Any) -> tuple[str, int | None, int | None]:
        """Extract source location from Slither object.

        Args:
            obj: Slither object with source_mapping.

        Returns:
            Tuple of (file_path, line_start, line_end).
        """
        source_mapping = getattr(obj, "source_mapping", None)
        if not source_mapping:
            return "unknown", None, None
        filename = (
            getattr(source_mapping, "filename_absolute", None)
            or getattr(source_mapping, "filename", None)
            or "unknown"
        )
        if hasattr(filename, "absolute"):
            filename = getattr(filename, "absolute")
        elif hasattr(filename, "used"):
            filename = getattr(filename, "used")
        file_path = self._relpath(str(filename))
        lines = getattr(source_mapping, "lines", None)
        if not lines:
            return file_path, None, None
        return file_path, min(lines), max(lines)

    def _relpath(self, filename: str) -> str:
        """Convert to relative path.

        Args:
            filename: Absolute filename.

        Returns:
            Relative path from project root.
        """
        try:
            return str(
                Path(filename).resolve().relative_to(self.ctx.project_root.resolve())
            )
        except Exception:
            return str(filename)

    def _source_slice(
        self, file_path: str | None, line_start: int | None, line_end: int | None
    ) -> str:
        """Get a slice of source code.

        Args:
            file_path: Path to source file.
            line_start: Starting line (1-indexed).
            line_end: Ending line (1-indexed).

        Returns:
            Source code slice.
        """
        if not file_path or line_start is None or line_end is None:
            return ""
        lines = self.ctx.get_source_lines(file_path)
        if not lines:
            return ""
        start = max(line_start - 1, 0)
        end = min(line_end, len(lines))
        return "\n".join(lines[start:end])

    def _node_id(
        self, kind: str, name: str, file_path: str | None, line_start: int | None
    ) -> str:
        """Generate a node ID using context helper.

        Args:
            kind: Node kind.
            name: Entity name.
            file_path: Source file path.
            line_start: Start line.

        Returns:
            Generated node ID.
        """
        # Use same hashing as legacy builder for compatibility
        import hashlib

        raw = f"{kind}:{name}:{file_path}:{line_start}"
        return f"{kind}:{hashlib.sha1(raw.encode('utf-8')).hexdigest()[:12]}"

    def _edge_id(self, edge_type: str, source: str, target: str) -> str:
        """Generate an edge ID.

        Args:
            edge_type: Type of edge.
            source: Source node ID.
            target: Target node ID.

        Returns:
            Generated edge ID.
        """
        import hashlib

        raw = f"{edge_type}:{source}:{target}"
        return f"edge:{hashlib.sha1(raw.encode('utf-8')).hexdigest()[:12]}"

    def _evidence(
        self, file_path: str | None, line_start: int | None, line_end: int | None
    ) -> list[Evidence]:
        """Create evidence list for a location.

        Args:
            file_path: Source file path.
            line_start: Start line.
            line_end: End line.

        Returns:
            List of Evidence objects.
        """
        if not file_path or file_path == "unknown":
            return []
        return [Evidence(file=file_path, line_start=line_start, line_end=line_end)]


def process_contract(ctx: BuildContext, contract: Any) -> Node:
    """Convenience function to process a contract.

    Args:
        ctx: BuildContext for shared state.
        contract: Slither contract object.

    Returns:
        Node representing the contract.
    """
    processor = ContractProcessor(ctx)
    return processor.process(contract)


def process_inheritance(ctx: BuildContext, contract: Any, contract_node: Node) -> None:
    """Convenience function to process contract inheritance.

    Args:
        ctx: BuildContext for shared state.
        contract: Slither contract object.
        contract_node: Node for the contract.
    """
    processor = ContractProcessor(ctx)
    processor.process_inheritance(contract, contract_node)
