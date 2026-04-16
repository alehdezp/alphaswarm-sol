"""Build the Project VKG from Solidity sources using Slither.

.. deprecated:: 2.0.0
    This module is deprecated. Use :mod:`alphaswarm_sol.kg.builder` instead,
    which provides the modular VKGBuilder with dependency injection,
    completeness reporting, and better testability.

    The modular builder is now the default and will be maintained going forward.
    This legacy module is preserved for reference only and will be removed in a
    future version.
"""

from __future__ import annotations

import warnings

# Emit deprecation warning on import
warnings.warn(
    "builder_legacy is deprecated. Use alphaswarm_sol.kg.builder instead.",
    DeprecationWarning,
    stacklevel=2,
)

import ast
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
import re
from typing import Any

import structlog
import yaml

from alphaswarm_sol.kg.heuristics import (
    classify_auth_modifiers,
    classify_state_var_name,
    is_privileged_state,
)
from alphaswarm_sol.kg.schema import Edge, Evidence, KnowledgeGraph, Node
from alphaswarm_sol.kg.solc import select_solc_for_file
from alphaswarm_sol.kg.taint import compute_dataflow, extract_inputs, extract_special_sources
from alphaswarm_sol.kg.operations import derive_all_operations, compute_behavioral_signature, compute_ordering_pairs
from alphaswarm_sol.kg.rich_edge import (
    RichEdge,
    RichEdgeEvidence,
    EdgeType,
    TaintSource,
    ExecutionContext,
    create_rich_edge,
    generate_meta_edges,
    compute_edge_risk_score,
    determine_pattern_tags,
)
from alphaswarm_sol.kg.classification import (
    NodeClassifier,
    FunctionRole,
    StateVariableRole,
    classify_function_role,
    classify_state_variable_role,
    detect_atomic_blocks,
)
from alphaswarm_sol.kg.paths import (
    PathEnumerator,
    ExecutionPath,
    generate_attack_scenarios,
    get_path_analysis_summary,
)
from alphaswarm_sol.kg.semgrep_compat import (
    ContractContext,
    FunctionContext,
    SECURITY_RULES,
    detect_semgrep_contract_rules,
    detect_semgrep_function_rules,
    has_bidi_chars,
)
from alphaswarm_sol.kg.solc import extract_missing_imports

try:
    import slither
    from slither import Slither
except Exception as exc:  # pragma: no cover - import error handled at runtime
    Slither = None  # type: ignore[assignment]
    slither = None  # type: ignore[assignment]
    _SLITHER_IMPORT_ERROR = exc
else:
    _SLITHER_IMPORT_ERROR = None


class VKGBuilder:
    """Construct a knowledge graph for a Solidity project."""

    def __init__(self, project_root: Path, *, exclude_dependencies: bool = True) -> None:
        self.project_root = project_root
        self.exclude_dependencies = exclude_dependencies
        self.logger = structlog.get_logger()
        self._source_cache: dict[str, list[str]] = {}

    def build(self, target: Path) -> KnowledgeGraph:
        if Slither is None:  # pragma: no cover - depends on user env
            raise RuntimeError(f"Slither is not available: {_SLITHER_IMPORT_ERROR}")

        self.logger.info("vkg_build_start", target=str(target))
        slither_kwargs = {"exclude_dependencies": self.exclude_dependencies}
        selected_solc_version = None
        if target.is_file():
            solc_selection = select_solc_for_file(target)
            if solc_selection:
                solc_bin, selected_solc_version = solc_selection
                slither_kwargs["solc"] = solc_bin
                self.logger.info(
                    "solc_selected",
                    target=str(target),
                    version=selected_solc_version,
                )
        try:
            slither = Slither(str(target), **slither_kwargs)
        except Exception as exc:  # pragma: no cover - depends on local solc
            self._log_compile_error(target, exc)
            raise

        graph = KnowledgeGraph(
            metadata={
                "root": str(self.project_root),
                "target": str(target),
                "created_at": datetime.now(timezone.utc).isoformat(),
                "builder": "slither",
                "slither_version": getattr(slither, "__version__", None),
                "solc_version_selected": selected_solc_version,
                "exclude_dependencies": self.exclude_dependencies,
            }
        )

        for contract in getattr(slither, "contracts", []):
            contract_node = self._add_contract(graph, contract)
            self._add_inheritance(graph, contract, contract_node)
            self._add_state_variables(graph, contract, contract_node)
            self._add_modifiers(graph, contract, contract_node)
            self._add_events(graph, contract, contract_node)
            self._add_functions(graph, contract, contract_node)
            self._annotate_cross_function_signals(graph, contract)
            invariants = self._add_invariants(graph, contract, contract_node)
            self._update_functions_for_invariants(graph, contract, invariants)

        # Phase 5: Generate RichEdges from function nodes
        self._generate_rich_edges(graph)

        # Phase 5: Generate meta-edges (SIMILAR_TO, BUGGY_PATTERN_MATCH)
        self._generate_meta_edges(graph)

        # Phase 6: Classify nodes into semantic roles
        self._classify_nodes(graph)

        # Phase 7: Execution path analysis (optional, for larger graphs)
        self._analyze_execution_paths(graph)

        self.logger.info(
            "vkg_build_complete",
            nodes=len(graph.nodes),
            edges=len(graph.edges),
            rich_edges=len(graph.rich_edges),
            meta_edges=len(graph.meta_edges),
        )
        return graph

    def _add_contract(self, graph: KnowledgeGraph, contract: Any) -> Node:
        file_path, line_start, line_end = self._source_location(contract)
        kind = "contract"
        if getattr(contract, "is_interface", False):
            kind = "interface"
        elif getattr(contract, "is_library", False):
            kind = "library"

        function_names = [fn.name for fn in getattr(contract, "functions", []) if getattr(fn, "name", None)]
        lowered_function_names = [name.lower() for name in function_names]
        has_initializer = any("initialize" in name for name in lowered_function_names)
        has_upgrade = any(name.startswith("upgrade") for name in lowered_function_names)
        is_proxy_like = "proxy" in contract.name.lower() or "upgradeable" in contract.name.lower()
        proxy_type = self._detect_proxy_type(contract)
        has_storage_gap, storage_gap_sizes = self._storage_gap_info(contract)
        upgradeable_without_storage_gap = (has_upgrade or is_proxy_like) and not has_storage_gap
        state_vars = getattr(contract, "state_variables", []) or []
        state_var_names = [getattr(var, "name", "") or "" for var in state_vars]
        lowered_state_var_names = [name.lower() for name in state_var_names if name]
        state_var_count = len(state_vars)
        owner_is_single_address = self._owner_is_single_address(state_vars)
        owner_uninitialized = self._owner_uninitialized(state_vars)
        has_timelock = any("timelock" in name or "time_lock" in name for name in lowered_state_var_names)
        has_timelock = has_timelock or any("timelock" in name for name in lowered_function_names)
        has_multisig = "multisig" in contract.name.lower()
        has_multisig = has_multisig or any(
            token in name for token in ("multisig", "multi_sig", "threshold", "signer", "signers", "owners")
            for name in lowered_state_var_names
        )
        has_multisig = has_multisig or any(
            token in name for token in ("multisig", "threshold", "signer", "signers")
            for name in lowered_function_names
        )
        has_role_grant = any(
            token in name for token in ("grant", "addrole", "setrole", "assignrole")
            for name in lowered_function_names
        )
        has_role_revoke = any(
            token in name for token in ("revoke", "removerole", "revokerole")
            for name in lowered_function_names
        )
        has_default_admin_role = any(
            token in name
            for token in ("default_admin", "defaultadmin", "default_admin_role", "defaultadminrole")
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
        has_oracle_state = any(
            token in name
            for token in ("oracle", "pricefeed", "aggregator")
            for name in lowered_state_var_names
        )
        has_oracle_feed_setter = any(
            token in name
            for token in ("setoracle", "setpricefeed", "setfeed", "setaggregator", "setchainlink")
            for name in lowered_function_names
        )
        has_inheritance = bool(getattr(contract, "inheritance", []) or [])
        has_composition = self._contract_has_composition(contract)
        inherits_erc2771 = any(
            "erc2771" in base.name.lower()
            for base in getattr(contract, "inheritance", []) or []
            if getattr(base, "name", None)
        )
        has_multicall = any("multicall" in name for name in lowered_function_names)
        file_text = ""
        if file_path and file_path != "unknown":
            file_text = "\n".join(self._source_lines(file_path))
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
        constructor_present = "constructor" in contract_source_clean
        initializers_disabled = "_disableinitializers" in contract_source_clean or "disableinitializers" in contract_source_clean
        if not initializers_disabled and constructor_present:
            if re.search(r"\b_initialized\s*=\s*type\s*\(\s*uint8\s*\)\s*\.max", contract_source_clean):
                initializers_disabled = True
            elif re.search(r"\b_initialized\s*=\s*1\b", contract_source_clean):
                initializers_disabled = True
            elif re.search(r"\b_initialized\s*=\s*true\b", contract_source_clean):
                initializers_disabled = True
            elif re.search(r"\binitialized\s*=\s*true\b", contract_source_clean):
                initializers_disabled = True
        contract_has_selfdestruct = "selfdestruct" in contract_source_clean or "suicide" in contract_source_clean
        state_var_names = [
            getattr(var, "name", "") or ""
            for var in getattr(contract, "state_variables", []) or []
        ]
        gap_indices = [idx for idx, name in enumerate(state_var_names) if "gap" in name.lower()]
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
        function_names = [
            fn.name
            for fn in getattr(contract, "functions", []) or []
            if getattr(fn, "name", None)
        ]
        lowered_function_names = [name.lower() for name in function_names]
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

        node_id = self._node_id(kind, contract.name, file_path, line_start)
        contract_rules = detect_semgrep_contract_rules(
            ContractContext(
                name=contract.name,
                is_proxy_like=is_proxy_like,
                has_storage_gap=has_storage_gap,
                state_var_count=state_var_count,
                inherits_erc2771=inherits_erc2771,
                has_multicall=has_multicall,
                has_bidi_chars=bidi_present,
            )
        )
        node = Node(
            id=node_id,
            type="Contract",
            label=contract.name,
            properties={
                "kind": kind,
                "has_initializer": has_initializer,
                "has_upgrade_function": has_upgrade,
                "is_proxy_like": is_proxy_like,
                "proxy_type": proxy_type,
                "has_storage_gap": has_storage_gap,
                "storage_gap_sizes": storage_gap_sizes,
                "upgradeable_without_storage_gap": upgradeable_without_storage_gap,
                "is_upgradeable": is_upgradeable,
                "is_uups_proxy": is_uups_proxy,
                "is_beacon_proxy": is_beacon_proxy,
                "is_diamond_proxy": is_diamond_proxy,
                "is_implementation_contract": is_implementation_contract,
                "has_constructor": constructor_present,
                "initializers_disabled": initializers_disabled,
                "has_selfdestruct": contract_has_selfdestruct,
                "storage_layout_changed": storage_layout_changed,
                "new_variables_not_at_end": new_variables_not_at_end,
                "inherited_storage_conflict": inherited_storage_conflict,
                "diamond_storage_isolation": diamond_storage_isolation,
                "uses_libdiamond": uses_libdiamond,
                "contract_has_beacon_state": contract_has_beacon_state,
                "contract_has_diamond_cut": contract_has_diamond_cut,
                "owner_is_single_address": owner_is_single_address,
                "owner_uninitialized": owner_uninitialized,
                "has_timelock": has_timelock,
                "has_multisig": has_multisig,
                "has_role_grant": has_role_grant,
                "has_role_revoke": has_role_revoke,
                "has_default_admin_role": has_default_admin_role,
                "has_role_events": has_role_events,
                "default_admin_address_is_zero": default_admin_address_is_zero,
                "has_role_enumeration": has_role_enumeration,
                "has_governance": has_governance,
                "has_withdraw": contract_has_withdraw,
                "has_emergency_withdraw": contract_has_emergency_withdraw,
                "has_emergency_pause": contract_has_emergency_pause,
                "multisig_threshold_is_one": multisig_threshold_is_one,
                "multisig_threshold_is_zero": multisig_threshold_is_zero,
                "timelock_delay_zero": timelock_delay_zero,
                "has_oracle_state": has_oracle_state,
                "has_oracle_feed_setter": has_oracle_feed_setter,
                "has_inheritance": has_inheritance,
                "has_inherited_contracts": has_inheritance,
                "has_composition": has_composition,
                "has_diamond_inheritance": has_diamond_inheritance,
                "shadows_parent_variable": shadows_parent_variable,
                "compiler_version_lt_08": compiler_version_lt_08,
                "uses_safemath": uses_safemath,
                "has_uninitialized_storage": has_uninitialized_storage,
                "has_uninitialized_boolean": has_uninitialized_boolean,
                "has_privileged_operations": privileged_summary["has_privileged_operations"],
                "has_unprotected_privileged_writes": privileged_summary[
                    "has_unprotected_privileged_writes"
                ],
                "has_protected_privileged_writes": privileged_summary[
                    "has_protected_privileged_writes"
                ],
                "has_inconsistent_access_control": privileged_summary[
                    "has_inconsistent_access_control"
                ],
                "state_var_count": state_var_count,
                "inherits_erc2771": inherits_erc2771,
                "has_multicall": has_multicall,
                "has_bidi_chars": bidi_present,
                "semgrep_like_rules": sorted(contract_rules),
                "semgrep_like_count": len(contract_rules),
                "file": file_path,
                "line_start": line_start,
                "line_end": line_end,
            },
            evidence=self._evidence(file_path, line_start, line_end),
        )
        return graph.add_node(node)

    def _add_inheritance(self, graph: KnowledgeGraph, contract: Any, contract_node: Node) -> None:
        for base in getattr(contract, "inheritance", []):
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
            graph.add_node(base_node)
            graph.add_edge(
                Edge(
                    id=self._edge_id("INHERITS", contract_node.id, base_id),
                    type="INHERITS",
                    source=contract_node.id,
                    target=base_id,
                    evidence=self._evidence(contract_node.properties.get("file"), None, None),
                )
            )

    def _add_state_variables(self, graph: KnowledgeGraph, contract: Any, contract_node: Node) -> None:
        for var in getattr(contract, "state_variables", []):
            file_path, line_start, line_end = self._source_location(var)
            node_id = self._node_id("state", f"{contract.name}.{var.name}", file_path, line_start)
            var_type = getattr(var, "type", None)
            security_tags = classify_state_var_name(var.name)
            node = Node(
                id=node_id,
                type="StateVariable",
                label=var.name,
                properties={
                    "type": str(var_type) if var_type is not None else None,
                    "visibility": getattr(var, "visibility", None),
                    "security_tags": security_tags,
                    "file": file_path,
                    "line_start": line_start,
                    "line_end": line_end,
                },
                evidence=self._evidence(file_path, line_start, line_end),
            )
            graph.add_node(node)
            graph.add_edge(
                Edge(
                    id=self._edge_id("CONTAINS_STATE_VAR", contract_node.id, node_id),
                    type="CONTAINS_STATE_VAR",
                    source=contract_node.id,
                    target=node_id,
                    evidence=self._evidence(file_path, line_start, line_end),
                )
            )

    def _add_modifiers(self, graph: KnowledgeGraph, contract: Any, contract_node: Node) -> None:
        for modifier in getattr(contract, "modifiers", []):
            file_path, line_start, line_end = self._source_location(modifier)
            node_id = self._node_id("modifier", f"{contract.name}.{modifier.name}", file_path, line_start)
            node = Node(
                id=node_id,
                type="Modifier",
                label=modifier.name,
                properties={
                    "visibility": getattr(modifier, "visibility", None),
                    "file": file_path,
                    "line_start": line_start,
                    "line_end": line_end,
                },
                evidence=self._evidence(file_path, line_start, line_end),
            )
            graph.add_node(node)
            graph.add_edge(
                Edge(
                    id=self._edge_id("CONTAINS_MODIFIER", contract_node.id, node_id),
                    type="CONTAINS_MODIFIER",
                    source=contract_node.id,
                    target=node_id,
                    evidence=self._evidence(file_path, line_start, line_end),
                )
            )

    def _add_events(self, graph: KnowledgeGraph, contract: Any, contract_node: Node) -> None:
        for event in getattr(contract, "events", []):
            file_path, line_start, line_end = self._source_location(event)
            node_id = self._node_id("event", f"{contract.name}.{event.name}", file_path, line_start)
            node = Node(
                id=node_id,
                type="Event",
                label=event.name,
                properties={
                    "file": file_path,
                    "line_start": line_start,
                    "line_end": line_end,
                },
                evidence=self._evidence(file_path, line_start, line_end),
            )
            graph.add_node(node)
            graph.add_edge(
                Edge(
                    id=self._edge_id("CONTAINS_EVENT", contract_node.id, node_id),
                    type="CONTAINS_EVENT",
                    source=contract_node.id,
                    target=node_id,
                    evidence=self._evidence(file_path, line_start, line_end),
                )
            )

    def _add_functions(self, graph: KnowledgeGraph, contract: Any, contract_node: Node) -> None:
        functions = getattr(contract, "functions", []) or []
        function_names = [fn.name for fn in functions if getattr(fn, "name", None)]
        lowered_function_names = [name.lower() for name in function_names]
        contract_is_proxy_like = "proxy" in contract.name.lower() or "upgradeable" in contract.name.lower()
        contract_has_upgrade_function = any(name.lower().startswith("upgrade") for name in function_names)
        contract_proxy_type = self._detect_proxy_type(contract)
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
        state_vars = getattr(contract, "state_variables", []) or []
        state_machine_vars = self._state_machine_var_names(state_vars)
        compiler_version_lt_08 = bool(contract_node.properties.get("compiler_version_lt_08"))
        contract_uses_safemath = bool(contract_node.properties.get("uses_safemath"))
        lowered_state_var_names = [
            (getattr(var, "name", "") or "").lower() for var in state_vars if getattr(var, "name", None)
        ]
        state_var_names = [getattr(var, "name", "") for var in state_vars if getattr(var, "name", None)]
        contract_has_beacon_state = any("beacon" in name.lower() for name in state_var_names if name)
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
        contract_has_multisig = "multisig" in contract.name.lower()
        contract_has_multisig = contract_has_multisig or any(
            token in name
            for token in ("multisig", "multi_sig", "threshold", "signer", "signers", "owners")
            for name in lowered_state_var_names
        )
        contract_has_multisig = contract_has_multisig or any(
            token in name
            for token in ("multisig", "threshold", "signer", "signers")
            for name in lowered_function_names
        )
        contract_has_governance = self._has_governance_signals(state_vars, lowered_function_names)
        contract_has_timelock = any(
            "timelock" in name or "time_lock" in name for name in lowered_state_var_names
        ) or any("timelock" in name.lower() for name in function_names)
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
        if getattr(contract, "is_interface", False):
            return
        for fn in functions:
            file_path, line_start, line_end = self._source_location(fn)
            label = self._function_label(fn)
            modifiers = [m.name for m in getattr(fn, "modifiers", []) if getattr(m, "name", None)]
            access_gate_mods = [m for m in modifiers if self._is_access_gate(m)]
            auth_patterns = classify_auth_modifiers(modifiers)
            has_reentrancy_guard = False
            has_only_owner = any(
                "onlyowner" in m.lower() or ("only" in m.lower() and "owner" in m.lower())
                for m in modifiers
            )
            has_only_role = any(
                "onlyrole" in m.lower() or ("only" in m.lower() and "role" in m.lower())
                for m in modifiers
            )
            external_calls = getattr(fn, "external_calls", []) or []
            high_level_calls = getattr(fn, "high_level_calls", []) or []
            internal_calls = getattr(fn, "internal_calls", []) or []
            high_level_calls = getattr(fn, "high_level_calls", []) or []
            visibility = getattr(fn, "visibility", None)
            calls_internal_functions = bool(internal_calls)
            reads_state = getattr(fn, "state_variables_read", []) or []
            writes_state = getattr(fn, "state_variables_written", []) or []
            state_read_targets = self._classify_state_read_targets(reads_state)
            state_write_targets = self._classify_state_write_targets(writes_state)
            writes_privileged_state = any(is_privileged_state(tags) for tags in state_write_targets.values())
            writes_sensitive_config = any(
                tag
                in {
                    "fee",
                    "config",
                    "reward",
                    "collateral",
                    "debt",
                    "liquidity",
                    "reserve",
                    "cap",
                    "oracle",
                    "treasury",
                    "governance",
                    "pause",
                    "allowlist",
                    "denylist",
                    "signer",
                    "dependency",
                }
                for tags in state_write_targets.values()
                for tag in tags
            )
            low_level_calls = getattr(fn, "low_level_calls", []) or []
            low_level_names = []
            for call in low_level_calls:
                for attr in ("name", "function_name", "full_name"):
                    name = getattr(call, attr, None)
                    if name:
                        low_level_names.append(str(name))
            low_level_names = [name for name in low_level_names if name]
            uses_delegatecall = any("delegatecall" in name.lower() for name in low_level_names)
            uses_call = any(name.lower() in {"call", "staticcall"} for name in low_level_names)
            # Enhanced: has_external_calls now includes both high-level and low-level calls
            has_external_calls = bool(external_calls) or bool(low_level_calls) or bool(high_level_calls)
            input_sources = extract_inputs(fn)
            special_sources = extract_special_sources(fn)
            has_user_input = bool(input_sources)
            parameters = getattr(fn, "parameters", []) or []
            parameter_names = [getattr(p, "name", None) for p in parameters if getattr(p, "name", None)]
            parameter_types = [str(getattr(p, "type", "") or "") for p in parameters]
            address_param_names = self._address_parameter_names(parameters)
            array_param_names = self._array_parameter_names(parameters)
            amount_param_names = self._amount_parameter_names(parameters)
            bytes_param_names = self._bytes_parameter_names(parameters)
            threshold_param_names = self._threshold_parameter_names(parameters)
            accepts_address_parameter = bool(address_param_names)
            has_array_parameter = bool(array_param_names)
            has_amount_parameter = bool(amount_param_names)
            has_bytes_parameter = bool(bytes_param_names)
            has_threshold_parameter = bool(threshold_param_names)
            has_pagination_parameter = bool(self._pagination_parameter_names(parameters))
            # Enhanced nonce parameter detection - detects naming variations
            # Detects: nonce, counter, sequence, sequenceNumber, index, txid, txnId, etc.
            NONCE_LIKE_NAMES = {"nonce", "counter", "sequence", "index", "txid", "txnid", "seqnum"}
            has_nonce_parameter = any(
                any(term in name.lower() for term in NONCE_LIKE_NAMES)
                for name in parameter_names
            )
            variables_read = getattr(fn, "variables_read", []) or []
            uses_msg_sender = self._uses_var_name(variables_read, "msg.sender")
            uses_tx_origin = self._uses_var_name(variables_read, "tx.origin")
            uses_msg_value = self._uses_var_name(variables_read, "msg.value")
            uses_block_timestamp = self._uses_var_name(variables_read, "block.timestamp")
            uses_block_number = self._uses_var_name(variables_read, "block.number")
            uses_block_hash = self._uses_var_name(variables_read, "blockhash")
            uses_block_prevrandao = self._uses_var_name(variables_read, "block.prevrandao")
            uses_chainid = self._uses_var_name(variables_read, "block.chainid")
            solidity_calls = getattr(fn, "solidity_calls", []) or []
            uses_ecrecover = any("ecrecover" in str(call) for call in solidity_calls)
            call_order = self._infer_call_order(fn)
            access_gate_logic, access_gate_sources = self._access_gate_from_predicates(fn)
            has_access_gate = bool(access_gate_mods) or access_gate_logic
            has_access_modifier = bool(access_gate_mods)
            has_require_msg_sender = "msg.sender" in access_gate_sources
            reads_nonce_state = self._state_var_name_match(reads_state, "nonce")
            writes_nonce_state = self._state_var_name_match(writes_state, "nonce")
            uses_domain_separator = self._state_var_name_match(reads_state, "domain_separator")
            require_exprs = self._require_expressions(fn)
            tx_origin_in_require = self._tx_origin_in_require(require_exprs)
            has_deadline_check = self._has_deadline_check(require_exprs, parameter_names)
            has_deadline_future_check = self._has_deadline_future_check(require_exprs, parameter_names)
            has_deadline_min_buffer = self._has_deadline_min_buffer(require_exprs, parameter_names)
            has_deadline_max = self._has_deadline_max(require_exprs, parameter_names)
            has_initializer_modifier = self._has_initializer_modifier(modifiers)
            has_only_proxy_modifier = self._has_only_proxy_modifier(modifiers)
            checks_initialized_flag = self._checks_initialized_flag(require_exprs)
            access_control_uses_or = self._access_gate_uses_or(require_exprs)
            time_based_access_control = self._has_block_timestamp_check(require_exprs)
            validates_delegatecall_target = self._validates_delegatecall_target(require_exprs, parameter_names)
            call_target_validated = self._validates_call_target(require_exprs, address_param_names)
            has_timelock_parameter = self._has_timelock_parameter(parameter_names)
            has_timelock_check = self._has_timelock_check(require_exprs, parameter_names)
            is_permit_like = "permit" in (getattr(fn, "name", "") or "").lower()
            token_call_kinds = self._token_call_kinds(fn)
            has_reentrancy_guard = self._has_reentrancy_guard(modifiers, require_exprs)
            uses_erc20_transfer = "transfer" in token_call_kinds
            uses_erc20_transfer_from = "transferfrom" in token_call_kinds
            uses_erc20_approve = "approve" in token_call_kinds
            # Moved after source_text_clean is defined (approves_infinite_amount below)
            approves_infinite_amount = False  # Placeholder, will be updated after source_text is available
            uses_erc20_mint = "mint" in token_call_kinds
            uses_erc20_burn = "burn" in token_call_kinds
            uses_erc721_safe_transfer = "safetransferfrom" in token_call_kinds
            uses_erc1155_safe_transfer = "safetransferfrom" in token_call_kinds
            uses_erc1155_safe_batch_transfer = "safebatchtransferfrom" in token_call_kinds
            uses_erc777_send = "send" in token_call_kinds
            uses_erc777_operator_send = "operatorsend" in token_call_kinds
            uses_erc777_burn = "burn" in token_call_kinds
            uses_erc777_mint = "mint" in token_call_kinds
            uses_erc4626_deposit = "deposit" in token_call_kinds
            uses_erc4626_withdraw = "withdraw" in token_call_kinds
            uses_erc4626_redeem = "redeem" in token_call_kinds
            uses_erc4626_mint = "mint" in token_call_kinds
            uses_safe_erc20 = any(kind.startswith("safe") for kind in token_call_kinds)
            checks_token_call_return = self._checks_token_call_return(require_exprs)
            token_return_guarded = False
            checks_zero_address = self._checks_zero_address(require_exprs)
            checks_sig_v = self._checks_sig_v(require_exprs, parameter_names)
            checks_sig_s = self._checks_sig_s(require_exprs, parameter_names)
            reads_oracle_price = self._reads_oracle_price(token_call_kinds)
            reads_dex_reserves = "getreserves" in token_call_kinds
            reads_pool_reserves = reads_dex_reserves
            oracle_call_count = self._oracle_call_count(fn)
            oracle_source_targets = self._oracle_call_targets(high_level_calls)
            has_staleness_check = self._has_staleness_check(require_exprs)
            has_staleness_threshold = self._has_staleness_threshold(require_exprs)
            has_deadline_parameter = self._has_deadline_parameter(parameter_names)
            has_slippage_parameter = self._has_slippage_parameter(parameter_names)
            has_slippage_check = self._has_slippage_check(require_exprs, parameter_names)
            has_minimum_output_parameter = has_slippage_parameter
            has_minimum_output = has_slippage_parameter
            has_sequencer_uptime_check = self._has_sequencer_uptime_check(require_exprs)
            has_sequencer_grace_period = self._has_sequencer_grace_period(require_exprs)
            oracle_round_check = self._has_oracle_round_check(require_exprs)
            oracle_freshness_ok = bool(has_staleness_check and oracle_round_check)
            calls_chainlink_latest_round_data = "latestrounddata" in token_call_kinds
            calls_chainlink_decimals = "decimals" in token_call_kinds
            validates_answer_positive = self._validates_oracle_answer_positive(require_exprs)
            validates_updated_at_recent = self._validates_oracle_timestamp(require_exprs)
            validates_answered_in_round_matches_round_id = oracle_round_check
            has_v3_struct_params = self._has_v3_struct_params(fn)
            swap_like = self._is_swap_like(getattr(fn, "name", "") or "", token_call_kinds, parameter_names)
            risk_missing_slippage_parameter = swap_like and not has_slippage_parameter
            risk_missing_deadline_parameter = swap_like and not has_deadline_parameter
            risk_missing_slippage_check = has_slippage_parameter and not has_slippage_check
            risk_missing_deadline_check = has_deadline_parameter and not has_deadline_check
            performs_swap_or_trade = swap_like
            performs_swap = swap_like
            interacts_with_amm = bool(swap_like or reads_dex_reserves or reads_pool_reserves)
            affects_price = bool(
                swap_like or reads_dex_reserves or reads_pool_reserves or reads_oracle_price
            )
            has_signature_validity_checks = bool(uses_ecrecover and checks_zero_address and has_deadline_check)
            is_upgrade_function = self._is_upgrade_function(fn)
            is_initializer_function = self._is_initializer_function(fn)
            upgrade_guarded = bool(is_upgrade_function and has_access_gate)
            has_access_control = bool(
                has_access_gate or has_access_modifier or has_only_owner or has_only_role
            )
            loop_summary, loop_nodes = self._analyze_loops(fn, parameter_names, reads_state)
            has_require_bounds = self._has_require_bounds(require_exprs, parameter_names)
            uses_transfer = self._uses_transfer(fn)
            uses_send = self._uses_send(fn)
            # has_strict_equality_check computed below after source_text is available
            has_strict_equality_check = False  # Placeholder
            state_mutability = self._normalize_state_mutability(fn)
            is_view = state_mutability == "view"
            is_withdraw_like = self._is_withdraw_like(getattr(fn, "name", "") or "")
            is_deposit_like = self._is_deposit_like(getattr(fn, "name", "") or "")
            is_mint_like = self._is_mint_like(getattr(fn, "name", "") or "")
            is_burn_like = self._is_burn_like(getattr(fn, "name", "") or "")
            is_reward_like = self._is_reward_like(getattr(fn, "name", "") or "")
            is_liquidation_like = self._is_liquidation_like(getattr(fn, "name", "") or "")
            uses_balance_of = "balanceof" in token_call_kinds
            balance_of_used_for_state_mutation = bool(uses_balance_of and writes_state)
            uses_total_supply = "totalsupply" in token_call_kinds
            has_balance_check = self._has_balance_check(require_exprs)
            checks_received_amount = self._checks_received_amount(require_exprs)
            has_pause_check = self._has_pause_check(require_exprs)
            uses_allowance_adjust = self._uses_allowance_adjust(token_call_kinds)
            source_text = self._function_source_text(file_path, line_start, line_end)
            source_text_lower = source_text.lower()
            source_text_clean = self._strip_comments(source_text_lower)
            # Now properly compute approves_infinite_amount and has_strict_equality_check
            approves_infinite_amount = uses_erc20_approve and self._approves_infinite_amount(source_text_clean)
            has_strict_equality_check = self._has_strict_equality_check(require_exprs, source_text_clean)
            has_nested_loop = bool(
                loop_summary["has_nested_loop"] or self._has_nested_loop_text(source_text_clean)
            )
            custom_return_guard = self._has_custom_return_guard(source_text_lower)
            token_return_guarded = bool(
                checks_token_call_return or uses_safe_erc20 or custom_return_guard
            )
            reads_twap = self._reads_twap(token_call_kinds, source_text_lower)
            has_twap_window_parameter = self._has_twap_window_parameter(parameter_names)
            reads_twap_with_window = reads_twap and has_twap_window_parameter
            has_twap_validation = bool(reads_twap or reads_twap_with_window)
            risk_missing_twap_window = reads_twap and not has_twap_window_parameter
            l2_oracle_context = self._l2_oracle_context(reads_state, contract, require_exprs, source_text_lower)
            is_callback = self._is_callback_function(fn)
            flash_loan_callback = self._is_flash_loan_callback(getattr(fn, "name", "") or "")
            flash_loan_initiator_checked = self._has_flash_loan_initiator_check(require_exprs)
            flash_loan_repayment_checked = self._has_flash_loan_repayment_check(require_exprs)
            flash_loan_asset_checked = self._has_flash_loan_asset_check(require_exprs)
            flash_loan_validation = bool(
                flash_loan_initiator_checked
                and flash_loan_repayment_checked
                and flash_loan_asset_checked
            )
            flash_loan_guard = self._has_flash_loan_guard(modifiers)
            flash_loan_sensitive_operation = bool(reads_oracle_price or reads_dex_reserves or reads_twap or swap_like)
            value_transfer_hint = bool(
                uses_transfer
                or uses_send
                or uses_erc20_transfer
                or uses_erc20_transfer_from
                or uses_erc721_safe_transfer
                or uses_erc1155_safe_transfer
                or uses_erc1155_safe_batch_transfer
            )
            price_result = self._price_input_used_in_calc(source_text_lower)
            if isinstance(price_result, tuple):
                price_input_used_in_calc, price_input_vars = price_result
            else:
                price_input_used_in_calc = bool(price_result)
                price_input_vars = set()
            price_input_value_sink = self._price_input_used_in_value_sink(
                source_text_lower,
                price_input_vars,
                state_var_names,
            )
            price_input_flows_to_value = bool(
                price_input_used_in_calc
                and price_input_value_sink
                and (
                    reads_dex_reserves
                    or reads_oracle_price
                    or reads_twap
                )
                and (writes_state or value_transfer_hint or is_mint_like or is_withdraw_like or is_deposit_like)
            )
            uses_price_for_value_calculation = bool(
                (reads_dex_reserves or reads_oracle_price or reads_twap)
                and (writes_state or value_transfer_hint or is_mint_like or is_withdraw_like or is_deposit_like)
            )
            oracle_source_count = len(oracle_source_targets)
            if reads_oracle_price and oracle_source_count == 0 and oracle_call_count:
                oracle_source_count = 1
            has_multi_source_oracle = oracle_source_count > 1
            reads_balance_or_reserves = bool(uses_balance_of or reads_dex_reserves)
            balance_used_for_pricing_or_voting = bool(
                reads_balance_or_reserves
                and (uses_price_for_value_calculation or self._fn_name_has_voting_tokens(label))
            )
            pool_reserves_used_in_swap = bool(reads_pool_reserves and swap_like)
            balance_used_for_rewards = bool(reads_balance_or_reserves and is_reward_like)
            pool_reserves_used_in_liquidation = bool(reads_pool_reserves and is_liquidation_like)
            uses_oracle_price_in_liquidation = bool(reads_oracle_price and is_liquidation_like)
            uses_historical_snapshot = self._uses_snapshot(label, parameter_names, require_exprs)
            governance_vote_without_snapshot = bool(
                self._fn_name_has_voting_tokens(label)
                and reads_balance_or_reserves
                and not uses_historical_snapshot
            )
            governance_quorum_without_snapshot = bool(
                self._fn_name_has_voting_tokens(label)
                and (reads_balance_or_reserves or uses_total_supply)
                and not uses_historical_snapshot
            )
            is_multisig_threshold_change = self._is_multisig_threshold_change(label, parameter_names)
            is_multisig_member_change = self._is_multisig_member_change(label, parameter_names)
            public_wrapper_without_access_gate = bool(
                visibility in {"public", "external"} and calls_internal_functions and not has_access_gate
            )
            multisig_threshold_change_without_gate = bool(
                contract_has_multisig
                and is_multisig_threshold_change
                and writes_state
                and not has_access_gate
            )
            multisig_signer_change_without_gate = bool(
                contract_has_multisig
                and is_multisig_member_change
                and writes_state
                and not has_access_gate
            )
            validates_address_nonzero = self._has_address_nonzero_check(require_exprs, address_param_names)
            has_threshold_check = self._has_parameter_bounds(require_exprs, threshold_param_names)
            has_fee_parameter = any("fee" in name.lower() for name in parameter_names)
            has_fee_bounds = self._has_named_bounds(require_exprs, parameter_names, {"fee", "fees"})
            multisig_threshold_change_without_validation = bool(
                contract_has_multisig
                and is_multisig_threshold_change
                and writes_state
                and not has_threshold_check
            )
            multisig_signer_change_without_validation = bool(
                contract_has_multisig
                and is_multisig_member_change
                and writes_state
                and not validates_address_nonzero
            )
            has_min_signer_check = self._has_min_signer_check(require_exprs)
            multisig_member_change_without_minimum_check = bool(
                contract_has_multisig
                and is_multisig_member_change
                and writes_state
                and not has_min_signer_check
            )
            has_threshold_vs_owner_check = self._has_threshold_vs_owner_check(require_exprs)
            multisig_threshold_change_without_owner_count_check = bool(
                contract_has_multisig
                and is_multisig_threshold_change
                and writes_state
                and not has_threshold_vs_owner_check
            )
            governance_exec_without_timelock_check = bool(
                contract_has_governance
                and contract_has_timelock
                and self._is_governance_execute_function(label)
                and not has_timelock_check
            )
            has_quorum_check = self._has_quorum_check(require_exprs)
            has_voting_period_check = self._has_voting_period_check(require_exprs)
            governance_exec_without_quorum_check = bool(
                contract_has_governance
                and self._is_governance_execute_function(label)
                and not has_quorum_check
            )
            governance_exec_without_vote_period_check = bool(
                contract_has_governance
                and self._is_governance_execute_function(label)
                and not has_voting_period_check
            )
            low_level_summary = self._summarize_low_level_calls(
                low_level_calls,
                parameter_names,
                require_exprs,
                getattr(fn, "nodes", []) or [],
            )
            external_call_target_user_controlled = self._external_call_target_user_controlled(
                external_calls, high_level_calls, parameter_names
            )
            has_untrusted_external_call = bool(
                low_level_summary["call_target_user_controlled"] or external_call_target_user_controlled
            )
            if low_level_summary["decodes_call_return"]:
                uses_abi_decode = True
            has_calldata_length_check = self._has_calldata_length_check(require_exprs)
            uses_abi_decode = "abi.decode" in source_text
            uses_selfdestruct = "selfdestruct" in source_text_clean or "suicide" in source_text_clean
            uses_extcodesize = "extcodesize" in source_text_lower or "code.length" in source_text_lower
            uses_extcodehash = "extcodehash" in source_text_lower
            uses_gasleft = "gasleft" in source_text_lower
            uses_merkle_proof = "merkle" in source_text
            uses_calldata_slice = self._uses_calldata_slice(source_text_lower)
            has_try_catch = "try " in source_text and "catch" in source_text
            string_param_names = [
                name
                for name, type_name in zip(parameter_names, parameter_types)
                if name and "string" in type_name.lower()
            ]
            bytes_or_string_param_names = bytes_param_names + string_param_names
            has_bytes_or_string_parameter = bool(bytes_or_string_param_names)
            has_bytes_length_check = self._has_bytes_length_check(
                require_exprs, bytes_or_string_param_names
            )
            uses_assert = "assert(" in source_text_lower
            uses_unchecked_block = "unchecked" in source_text_lower
            uses_arithmetic = self._uses_arithmetic(source_text_lower)
            uses_division = self._uses_division(source_text_lower)
            divisor_source = self._divisor_sources(source_text_lower, parameter_names, state_var_names)
            divisor_validated_nonzero = self._has_nonzero_check(
                require_exprs, parameter_names + state_var_names
            )
            allocates_memory_array_from_input = self._allocates_memory_array_from_input(
                source_text_lower, parameter_names
            )
            event_emission_in_loop = loop_summary["has_loops"] and "emit " in source_text_lower
            storage_growth_operation = any(
                f"{str(name).lower()}.push" in source_text_lower for name in array_state_var_names
            )
            mapping_growth_operation = bool(
                any(
                    f"{str(name).lower()}[" in source_text_lower
                    for name in mapping_state_var_names
                    if name
                )
                and writes_state
            )
            array_growth_unbounded = (
                storage_growth_operation
                and loop_summary["has_loops"]
                and loop_summary["has_unbounded_loop"]
                and any(name.lower() in source_text_lower for name in parameter_names or [])
            )
            mapping_growth_unbounded = (
                mapping_growth_operation
                and loop_summary["has_loops"]
                and loop_summary["has_unbounded_loop"]
                and any(
                    f"{param.lower()}" in source_text_lower
                    for param in parameter_names
                    if param and param.lower() not in {"n", "i"}
                )
            )
            recursive_call = self._has_recursive_call(label, source_text_lower)
            calldata_slice_without_check = bool(uses_calldata_slice and not has_calldata_length_check)
            recursive_call_without_guard = bool(
                recursive_call and has_user_input and not has_require_bounds
            )
            mapping_iteration_in_loop = bool(
                loop_summary["has_loops"]
                and any(
                    str(name).lower() in source_text_lower for name in mapping_state_var_names if name
                )
            )
            has_abi_decode_guard = bool(
                has_calldata_length_check or has_try_catch or low_level_summary["checks_returndata_length"]
            )
            merkle_leaf_domain_separated = self._has_merkle_leaf_domain_separator(source_text)
            validates_address_not_self = self._has_address_not_self_check(require_exprs, address_param_names)
            validates_contract_code = self._has_contract_code_check(require_exprs)
            address_parameter_used_for_transfer = bool(
                accepts_address_parameter
                and (
                    uses_erc20_transfer
                    or uses_erc20_transfer_from
                    or uses_erc721_safe_transfer
                    or uses_erc1155_safe_transfer
                    or uses_erc1155_safe_batch_transfer
                    or uses_transfer
                    or uses_send
                )
            )
            address_parameter_used_for_call = bool(
                accepts_address_parameter
                and (uses_call or uses_delegatecall or low_level_summary["call_target_user_controlled"])
            )
            has_push_payment = bool(
                uses_transfer or uses_send or low_level_summary["has_call_with_value"]
            )
            payment_recipient_controllable = bool(
                address_parameter_used_for_transfer or low_level_summary["call_target_user_controlled"]
            )
            handles_transfer_failure = bool(
                low_level_summary["checks_low_level_call_success"]
                or self._handles_transfer_failure(require_exprs, source_text_lower)
            )
            is_auction_like = any(token in label.lower() for token in ("auction", "bid"))
            has_amount_bounds = self._has_amount_bounds(require_exprs, amount_param_names)
            has_amount_nonzero_check = self._has_amount_nonzero_check(require_exprs, amount_param_names)
            uses_amount_division = self._uses_amount_division(amount_param_names, source_text_lower)
            has_precision_guard = self._has_precision_guard(require_exprs, source_text_lower)
            has_unchecked_block = "unchecked" in source_text_lower
            has_arithmetic = self._has_arithmetic_ops(source_text_lower)
            has_division = self._has_division(source_text_lower)
            has_multiplication = self._has_multiplication(source_text_lower)
            division_before_multiplication = self._division_before_multiplication(source_text_lower)
            in_financial_context = self._in_financial_context(
                source_text_lower, state_read_targets, state_write_targets
            )
            unchecked_contains_arithmetic = bool(has_unchecked_block and has_arithmetic)
            unchecked_operand_from_user = self._unchecked_uses_parameters(source_text_lower, parameter_names)
            unchecked_affects_balance = bool(
                has_unchecked_block
                and (
                    self._has_state_tag(state_read_targets, "balance")
                    or self._has_state_tag(state_write_targets, "balance")
                )
            )
            has_explicit_cast = self._has_explicit_cast(source_text_lower)
            cast_is_narrowing = self._cast_is_narrowing(source_text_lower)
            has_bounds_check_before_cast = self._has_bounds_check_before_cast(require_exprs, parameter_names)
            has_signed_to_unsigned_cast = self._has_signed_to_unsigned_cast(source_text_lower, parameter_types)
            has_signed_check = self._has_signed_check(require_exprs, parameter_names)
            has_address_to_uint_cast = self._has_address_to_uint_cast(source_text_lower, address_param_names)
            divisor_validated_nonzero = self._divisor_validated_nonzero(require_exprs, parameter_names)
            has_rounding_ops = self._has_rounding_ops(source_text_lower)
            large_number_multiplication = self._large_number_multiplication(source_text_lower)
            price_amount_multiplication = self._price_amount_multiplication(source_text_lower)
            percentage_calculation = self._percentage_calculation(source_text_lower)
            percentage_bounds_check = self._percentage_bounds_check(require_exprs, parameter_names)
            basis_points_calculation = self._basis_points_calculation(source_text_lower)
            ratio_calculation = self._ratio_calculation(source_text_lower)
            fee_calculation = self._fee_calculation(source_text_lower)
            fee_accumulation = self._fee_accumulation(source_text_lower)
            timestamp_arithmetic = self._timestamp_arithmetic(source_text_lower)
            uses_token_decimals = self._uses_token_decimals(source_text_lower)
            decimal_scaling_usage = self._decimal_scaling_usage(source_text_lower)
            decimal_normalization = self._has_decimal_normalization(source_text_lower)
            if not compiler_version_lt_08 and file_path:
                compiler_version_lt_08 = self._is_pre_08_pragma(self._source_slice(file_path, 1, 5))
            uses_safemath = bool(contract_uses_safemath or "safemath" in source_text_lower)
            uses_muldiv_or_safemath = self._uses_muldiv_or_safemath(source_text_lower)
            loop_counter_small_type = self._loop_counter_small_type(source_text_lower)
            pre_08_arithmetic = bool(compiler_version_lt_08 and has_arithmetic and not uses_safemath)
            has_array_length_check = self._has_array_length_check(require_exprs, array_param_names)
            has_array_length_match = self._has_array_length_match(require_exprs, array_param_names)
            has_array_index_check = self._has_array_index_check(
                require_exprs, array_param_names, parameter_names
            )
            has_multi_array_parameter = len(array_param_names) > 1
            has_oracle_aggregation_sanity = self._has_oracle_aggregation_sanity(require_exprs, source_text)
            has_oracle_decimals_normalized = self._has_oracle_decimals_normalized(source_text_lower, require_exprs)
            has_oracle_min_source_count = self._has_oracle_min_source_count(require_exprs)
            has_oracle_per_source_staleness = self._has_oracle_per_source_staleness(require_exprs)
            has_oracle_time_alignment = self._has_oracle_time_alignment(require_exprs)
            has_oracle_weighted_aggregation = self._has_oracle_weighted_aggregation(source_text_lower, require_exprs)
            has_oracle_circuit_breaker = self._has_oracle_circuit_breaker(source_text_lower, require_exprs)
            has_oracle_disagreement_fallback = self._has_oracle_disagreement_fallback(
                source_text_lower, require_exprs
            )
            has_oracle_min_agreement = self._has_oracle_min_agreement(source_text_lower, require_exprs)
            has_oracle_source_health_check = self._has_oracle_source_health_check(
                source_text_lower, require_exprs
            )
            has_oracle_update_frequency_alignment = self._has_oracle_update_frequency_alignment(
                source_text_lower, require_exprs
            )
            oracle_update_function = self._is_oracle_update_function(label)
            has_oracle_update_rate_limit = self._has_oracle_update_rate_limit(require_exprs, source_text_lower)
            has_oracle_update_timelock = self._has_oracle_update_timelock(require_exprs, source_text_lower)
            has_oracle_update_deviation_check = self._has_oracle_update_deviation_check(require_exprs, source_text_lower)
            has_oracle_update_signature_check = self._has_oracle_update_signature_check(source_text_lower)
            has_oracle_update_sequence_check = self._has_oracle_update_sequence_check(require_exprs, source_text_lower)
            has_oracle_update_timestamp_check = self._has_oracle_update_timestamp_check(require_exprs)
            has_cross_chain_context = self._has_cross_chain_context(reads_state, contract, source_text)
            has_cross_chain_validation = self._has_cross_chain_validation(require_exprs, source_text)
            has_bridge_replay_protection = self._has_bridge_replay_protection(require_exprs, source_text_lower)
            has_cross_chain_consistency_check = self._has_cross_chain_consistency_check(
                require_exprs, source_text_lower
            )
            has_bridge_finality_check = self._has_bridge_finality_check(require_exprs, source_text_lower)
            has_bridge_source_chain_check = self._has_bridge_source_chain_check(
                source_text_lower, require_exprs
            )
            has_bridge_ordering_check = self._has_bridge_ordering_check(source_text_lower, require_exprs)
            has_l2_finality_check = self._has_l2_finality_check(require_exprs, source_text_lower)
            uses_fixed_oracle_decimals = self._uses_fixed_oracle_decimals(source_text)
            has_duration_parameter = self._has_duration_parameter(parameter_names)
            has_duration_bounds = self._has_duration_bounds(require_exprs, parameter_names)
            label_lower = label.lower()
            locks_funds = bool(
                writes_state and any(token in label_lower for token in ("lock", "freeze", "pause"))
            )
            unlock_condition_external_dependent = bool("unlock" in label_lower and has_external_calls)
            unlock_condition_potentially_impossible = bool(
                "unlock" in label_lower
                and low_level_summary["has_low_level_calls"]
                and not low_level_summary["checks_low_level_call_success"]
                and not has_try_catch
            )
            time_lock_overflow_risk = bool(has_duration_parameter and not has_duration_bounds)
            has_external_data_integrity_check = bool(
                uses_ecrecover or has_cross_chain_validation or uses_merkle_proof
            )
            delegatecall_in_non_proxy = uses_delegatecall and not contract_is_proxy_like and not contract_has_upgrade_function
            delegatecall_in_proxy_upgrade_context = bool(
                uses_delegatecall
                and has_access_gate
                and (is_upgrade_function or has_only_proxy_modifier or contract_has_upgrade_function)
            )
            delegatecall_context_sensitive = uses_delegatecall and (uses_msg_sender or uses_tx_origin)
            bypassable_access_control = bool(
                (uses_delegatecall and low_level_summary["call_target_user_controlled"])
                or (is_callback and not has_access_gate)
                or (uses_call and low_level_summary["call_target_user_controlled"] and not has_access_gate)
            )
            cross_contract_auth_confusion = bool(
                (uses_delegatecall and delegatecall_context_sensitive)
                or (uses_tx_origin and has_external_calls)
                or (
                    low_level_summary["has_low_level_calls"]
                    and low_level_summary["call_target_user_controlled"]
                    and not has_access_gate
                )
            )
            reads_balance_state = self._has_state_tag(state_read_targets, "balance")
            writes_balance_state = self._has_state_tag(state_write_targets, "balance")
            reads_share_state = self._has_state_tag(state_read_targets, "shares")
            writes_share_state = self._has_state_tag(state_write_targets, "shares")
            reads_supply_state = self._has_state_tag(state_read_targets, "supply")
            writes_supply_state = self._has_state_tag(state_write_targets, "supply")
            writes_collateral_state = self._has_state_tag(state_write_targets, "collateral")
            writes_pool_state = self._has_state_tag(state_write_targets, "pool")
            reads_dependency_state = self._has_state_tag(state_read_targets, "dependency")
            balance_used_for_collateralization = self._balance_used_for_collateralization(
                label,
                parameter_names,
                reads_balance_or_reserves,
                reads_oracle_price,
                reads_dex_reserves,
                reads_twap,
            )
            pool_reserves_used_for_collateral = bool(reads_pool_reserves and balance_used_for_collateralization)
            contract_has_inheritance = bool(getattr(contract, "inheritance", []) or [])
            contract_has_composition = self._contract_has_composition(contract)
            external_call_contracts = self._external_call_contracts(external_calls, high_level_calls, contract.name)
            calls_external_contract = bool(external_call_contracts)
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
                and writes_state
                and not has_reentrancy_guard
            )
            contract_has_balance_tracking = self._contract_has_balance_tracking(contract)
            uses_erc721_safe_mint = "safemint" in token_call_kinds
            uses_erc1155_mint = "mint" in token_call_kinds and "bytes" in source_text_lower
            uses_erc1155_mint_batch = "mintbatch" in token_call_kinds
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
            has_twap_observation_check = self._has_twap_observation_check(require_exprs, source_text_lower)
            has_twap_window_min_check = self._has_twap_window_min_check(require_exprs, parameter_names)
            has_twap_timestamp_check = self._has_twap_timestamp_check(require_exprs)
            has_twap_price_bounds = self._has_twap_price_bounds(require_exprs)
            has_twap_gap_handling = self._has_twap_gap_handling(source_text_lower, require_exprs)
            has_twap_volatility_window = self._has_twap_volatility_window(source_text_lower, require_exprs)
            validates_started_at_recent = self._validates_oracle_started_at(require_exprs)
            transfers_eth = uses_transfer or uses_send or low_level_summary["has_call_with_value"]
            uses_fixed_gas_stipend = uses_transfer or uses_send or low_level_summary["has_hardcoded_gas"]
            modifies_roles = self._modifies_roles(state_write_targets, label)
            allows_self_modification = bool(modifies_roles and uses_msg_sender)
            is_privileged_operation = bool(writes_privileged_state or uses_transfer or uses_send or uses_call)
            can_affect_user_funds = bool(
                uses_erc20_transfer
                or uses_erc20_transfer_from
                or uses_transfer
                or uses_send
                or uses_call
            )
            is_admin_named = self._is_admin_named_function(label)
            role_grant_like = self._is_role_grant_like(label, parameter_names)
            role_revoke_like = self._is_role_revoke_like(label, parameter_names)
            is_emergency_function = self._is_emergency_function(label)
            is_multicall_function = "multicall" in label.lower()
            is_timelock_admin_function = self._is_timelock_admin_function(label)
            is_value_transfer = bool(
                transfers_eth
                or uses_erc20_transfer
                or uses_erc20_transfer_from
                or uses_erc721_safe_transfer
                or uses_erc1155_safe_transfer
                or uses_erc1155_safe_batch_transfer
            )
            modifies_state_machine_variable = bool(
                writes_state
                and state_machine_vars
                and any(getattr(var, "name", None) in state_machine_vars for var in writes_state)
            )
            validates_current_state = self._validates_current_state(require_exprs, state_machine_vars)
            enforces_valid_transition = validates_current_state
            allows_invalid_transition = bool(modifies_state_machine_variable and not validates_current_state)
            state_cleanup_missing = bool(modifies_state_machine_variable and self._state_cleanup_missing(source_text_lower))
            state_race_condition = self._state_race_condition(has_external_calls, writes_state, has_reentrancy_guard)
            accounting_update_missing = bool(is_value_transfer and not writes_balance_state and not writes_supply_state)
            double_counting_risk = self._double_counting_risk(
                source_text_lower, writes_balance_state, writes_supply_state
            )
            rounding_accumulation_risk = bool(has_rounding_ops and loop_summary["has_loops"])
            emits_event = "emit " in source_text_lower
            event_param_mismatch = self._event_param_mismatch(source_text_lower, parameter_names)
            override_missing_super = bool("override" in source_text_lower and "super." not in source_text_lower)
            selfdestruct_target_user_controlled = self._selfdestruct_target_user_controlled(
                source_text_lower, address_param_names
            )
            extcodesize_in_constructor = bool(uses_extcodesize and getattr(fn, "is_constructor", None))
            share_inflation_risk = self._share_inflation_risk(
                reads_share_state,
                writes_share_state,
                reads_supply_state,
                uses_amount_division,
                has_division,
                has_precision_guard,
                has_balance_check,
            )
            missing_return_value_check = bool(
                (uses_erc20_transfer or uses_call)
                and not token_return_guarded
                and not low_level_summary["checks_low_level_call_success"]
            )
            missing_amount_bounds = bool(has_amount_parameter and not has_amount_bounds)
            division_precision_risk = bool(has_division and not has_precision_guard)
            fee_precision_risk = bool(fee_calculation and not has_precision_guard)
            basis_points_precision_risk = bool(basis_points_calculation and not has_precision_guard)
            ratio_calculation_risk = bool(ratio_calculation and division_precision_risk)
            price_amount_overflow_risk = bool(price_amount_multiplication and not has_precision_guard)
            percentage_overflow_risk = bool(percentage_calculation and not percentage_bounds_check)
            token_decimal_mismatch = bool(uses_token_decimals and not decimal_normalization)
            unchecked_arithmetic_risk = bool(
                unchecked_contains_arithmetic and (unchecked_operand_from_user or unchecked_affects_balance)
            )
            division_by_zero_risk = bool(has_division and not divisor_validated_nonzero)
            signed_unsigned_cast_risk = bool(has_signed_to_unsigned_cast and not has_signed_check)
            narrowing_cast_risk = bool(has_explicit_cast and cast_is_narrowing and not has_bounds_check_before_cast)
            multiplication_overflow_risk = bool(large_number_multiplication and not uses_muldiv_or_safemath)
            fee_accumulation_overflow_risk = bool(fee_accumulation and (loop_summary["has_loops"] or has_multiplication))
            access_control_weak_source = bool(
                set(access_gate_sources)
                & {
                    "msg.value",
                    "block.timestamp",
                    "block.number",
                    "block.chainid",
                    "blockhash",
                    "block.prevrandao",
                }
            )
            access_gate_uses_balance_check = self._access_gate_uses_balance_check(require_exprs)
            access_gate_uses_contract_address = self._access_gate_uses_contract_address(require_exprs)
            access_gate_uses_hash_compare = self._access_gate_uses_hash_compare(require_exprs)
            access_gate_has_if_return = self._access_gate_has_if_return(source_text_lower)
            access_gate_without_sender_source = bool(
                self._has_non_sender_access_gate(require_exprs, parameter_names)
                and "msg.sender" not in access_gate_sources
                and "tx.origin" not in access_gate_sources
            )
            callable_via_multicall = bool(
                contract_has_multicall
                and getattr(fn, "visibility", None) in {"public", "external"}
                and "multicall" not in label.lower()
            )
            has_context_dependent_auth = bool(has_access_gate and (uses_msg_sender or uses_tx_origin))
            emergency_delegatecall_bypass = bool(
                is_emergency_function and uses_delegatecall and not validates_delegatecall_target
            )
            multicall_batching_without_guard = bool(
                is_multicall_function and has_external_calls and not has_reentrancy_guard
            )

            source_text = self._source_slice(file_path, line_start, line_end)
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

            # Derive semantic operations (Phase 1)
            semantic_ops_list = derive_all_operations(fn)
            semantic_op_names = [op.operation.name for op in semantic_ops_list]
            op_sequence = [
                {"op": op.operation.name, "order": op.cfg_order, "line": op.line_number}
                for op in sorted(semantic_ops_list, key=lambda x: x.cfg_order)
            ]
            behavioral_signature = compute_behavioral_signature(semantic_ops_list)
            op_ordering = compute_ordering_pairs(semantic_ops_list)

            node_id = self._node_id("function", f"{contract.name}.{label}", file_path, line_start)
            node = Node(
                id=node_id,
                type="Function",
                label=label,
                properties={
                    "visibility": getattr(fn, "visibility", None),
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
                    "has_untrusted_external_call": has_untrusted_external_call,
                    "has_internal_calls": bool(internal_calls),
                    "public_wrapper_without_access_gate": public_wrapper_without_access_gate,
                    "reads_state": bool(reads_state),
                    "writes_state": bool(writes_state),
                    "state_write_targets": sorted(
                        {tag for tags in state_write_targets.values() for tag in tags}
                    ),
                    "state_read_targets": sorted(
                        {tag for tags in state_read_targets.values() for tag in tags}
                    ),
                    "writes_privileged_state": writes_privileged_state,
                    "writes_sensitive_config": writes_sensitive_config,
                    "low_level_calls": low_level_names,
                    "has_low_level_calls": low_level_summary["has_low_level_calls"],
                    "low_level_call_count": low_level_summary["low_level_call_count"],
                    "uses_delegatecall": uses_delegatecall,
                    "uses_call": uses_call,
                    "delegatecall_in_non_proxy": delegatecall_in_non_proxy,
                    "delegatecall_in_proxy_upgrade_context": delegatecall_in_proxy_upgrade_context,
                    "delegatecall_context_sensitive": delegatecall_context_sensitive,
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
                    "has_bytes_or_string_parameter": has_bytes_or_string_parameter,
                    "has_bytes_length_check": has_bytes_length_check,
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
                    "balance_of_used_for_state_mutation": balance_of_used_for_state_mutation,
                    "uses_total_supply": uses_total_supply,
                    "checks_zero_address": checks_zero_address,
                    "checks_sig_v": checks_sig_v,
                    "checks_sig_s": checks_sig_s,
                    "reads_oracle_price": reads_oracle_price,
                    "reads_dex_reserves": reads_dex_reserves,
                    "reads_pool_reserves": reads_pool_reserves,
                    "has_staleness_check": has_staleness_check,
                    "has_staleness_threshold": has_staleness_threshold,
                    "has_deadline_parameter": has_deadline_parameter,
                    "has_deadline_future_check": has_deadline_future_check,
                    "has_deadline_min_buffer": has_deadline_min_buffer,
                    "has_deadline_max": has_deadline_max,
                    "has_duration_parameter": has_duration_parameter,
                    "has_duration_bounds": has_duration_bounds,
                    "has_slippage_parameter": has_slippage_parameter,
                    "has_slippage_check": has_slippage_check,
                    "has_minimum_output_parameter": has_minimum_output_parameter,
                    "has_minimum_output": has_minimum_output,
                    "reads_twap": reads_twap,
                    "has_twap_window_parameter": has_twap_window_parameter,
                    "has_twap_window_min_check": has_twap_window_min_check,
                    "reads_twap_with_window": reads_twap_with_window,
                    "has_twap_validation": has_twap_validation,
                    "has_twap_observation_check": has_twap_observation_check,
                    "has_twap_timestamp_check": has_twap_timestamp_check,
                    "has_twap_price_bounds": has_twap_price_bounds,
                    "has_twap_gap_handling": has_twap_gap_handling,
                    "has_twap_volatility_window": has_twap_volatility_window,
                    "has_sequencer_uptime_check": has_sequencer_uptime_check,
                    "has_sequencer_grace_period": has_sequencer_grace_period,
                    "has_l2_finality_check": has_l2_finality_check,
                    "l2_oracle_context": l2_oracle_context,
                    "oracle_round_check": oracle_round_check,
                    "oracle_freshness_ok": oracle_freshness_ok,
                    "calls_chainlink_latest_round_data": calls_chainlink_latest_round_data,
                    "calls_chainlink_decimals": calls_chainlink_decimals,
                    "validates_answer_positive": validates_answer_positive,
                    "validates_updated_at_recent": validates_updated_at_recent,
                    "validates_started_at_recent": validates_started_at_recent,
                    "validates_answered_in_round_matches_round_id": validates_answered_in_round_matches_round_id,
                    "handles_oracle_revert": has_try_catch,
                    "has_try_catch": has_try_catch,
                    "has_v3_struct_params": has_v3_struct_params,
                    "swap_like": swap_like,
                    "performs_swap_or_trade": performs_swap_or_trade,
                    "performs_swap": performs_swap,
                    "interacts_with_amm": interacts_with_amm,
                    "affects_price": affects_price,
                    "risk_missing_slippage_parameter": risk_missing_slippage_parameter,
                    "risk_missing_deadline_parameter": risk_missing_deadline_parameter,
                    "risk_missing_slippage_check": risk_missing_slippage_check,
                    "risk_missing_deadline_check": risk_missing_deadline_check,
                    "risk_missing_twap_window": risk_missing_twap_window,
                    "has_signature_validity_checks": has_signature_validity_checks,
                    "is_upgrade_function": is_upgrade_function,
                    "is_initializer_function": is_initializer_function,
                    "upgrade_guarded": upgrade_guarded,
                    "modifies_roles": modifies_roles,
                    "role_grant_like": role_grant_like,
                    "role_revoke_like": role_revoke_like,
                    "allows_self_modification": allows_self_modification,
                    "is_callback": is_callback,
                    "is_privileged_operation": is_privileged_operation,
                    "can_affect_user_funds": can_affect_user_funds,
                    "is_admin_named": is_admin_named,
                    "is_emergency_function": is_emergency_function,
                    "is_multicall_function": is_multicall_function,
                    "is_timelock_admin_function": is_timelock_admin_function,
                    "is_value_transfer": is_value_transfer,
                    "locks_funds": locks_funds,
                    "unlock_condition_external_dependent": unlock_condition_external_dependent,
                    "unlock_condition_potentially_impossible": unlock_condition_potentially_impossible,
                    "time_lock_overflow_risk": time_lock_overflow_risk,
                    "access_control_weak_source": access_control_weak_source,
                    "access_gate_uses_balance_check": access_gate_uses_balance_check,
                    "access_gate_uses_contract_address": access_gate_uses_contract_address,
                    "access_gate_uses_hash_compare": access_gate_uses_hash_compare,
                    "access_gate_has_if_return": access_gate_has_if_return,
                    "access_gate_without_sender_source": access_gate_without_sender_source,
                    "callable_via_multicall": callable_via_multicall,
                    "has_context_dependent_auth": has_context_dependent_auth,
                    "emergency_delegatecall_bypass": emergency_delegatecall_bypass,
                    "multicall_batching_without_guard": multicall_batching_without_guard,
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
                    "has_access_modifier": has_access_modifier,
                    "bypassable_access_control": bypassable_access_control,
                    "cross_contract_auth_confusion": cross_contract_auth_confusion,
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
                    "storage_growth_operation": storage_growth_operation,
                    "mapping_growth_operation": mapping_growth_operation,
                    "array_growth_unbounded": array_growth_unbounded,
                    "mapping_growth_unbounded": mapping_growth_unbounded,
                    "mapping_iteration_in_loop": mapping_iteration_in_loop,
                    "event_emission_in_loop": event_emission_in_loop,
                    "uses_transfer": uses_transfer,
                    "uses_send": uses_send,
                    "has_push_payment": has_push_payment,
                    "payment_recipient_controllable": payment_recipient_controllable,
                    "handles_transfer_failure": handles_transfer_failure,
                    "is_auction_like": is_auction_like,
                    "has_strict_equality_check": has_strict_equality_check,
                    "state_write_before_external_call": call_order.get("write_before_call"),
                    "state_write_after_external_call": call_order.get("write_after_call"),
                    "is_view": is_view,
                    "is_withdraw_like": is_withdraw_like,
                    "is_deposit_like": is_deposit_like,
                    "is_mint_like": is_mint_like,
                    "is_burn_like": is_burn_like,
                    "has_balance_check": has_balance_check,
                    "checks_received_amount": checks_received_amount,
                    "has_pause_check": has_pause_check,
                    "uses_allowance_adjust": uses_allowance_adjust,
                    "flash_loan_callback": flash_loan_callback,
                    "flash_loan_validation": flash_loan_validation,
                    "flash_loan_initiator_checked": flash_loan_initiator_checked,
                    "flash_loan_repayment_checked": flash_loan_repayment_checked,
                    "flash_loan_asset_checked": flash_loan_asset_checked,
                    "flash_loan_guard": flash_loan_guard,
                    "flash_loan_sensitive_operation": flash_loan_sensitive_operation,
                    "uses_price_for_value_calculation": uses_price_for_value_calculation,
                    "price_input_flows_to_value": price_input_flows_to_value,
                    "has_multi_source_oracle": has_multi_source_oracle,
                    "oracle_source_count": oracle_source_count,
                    "reads_balance_or_reserves": reads_balance_or_reserves,
                    "balance_used_for_pricing_or_voting": balance_used_for_pricing_or_voting,
                    "pool_reserves_used_in_swap": pool_reserves_used_in_swap,
                    "balance_used_for_rewards": balance_used_for_rewards,
                    "balance_used_for_collateralization": balance_used_for_collateralization,
                    "pool_reserves_used_for_collateral": pool_reserves_used_for_collateral,
                    "pool_reserves_used_in_liquidation": pool_reserves_used_in_liquidation,
                    "uses_oracle_price_in_liquidation": uses_oracle_price_in_liquidation,
                    "uses_historical_snapshot": uses_historical_snapshot,
                    "governance_vote_without_snapshot": governance_vote_without_snapshot,
                    "governance_quorum_without_snapshot": governance_quorum_without_snapshot,
                    "multisig_threshold_change_without_gate": multisig_threshold_change_without_gate,
                    "multisig_signer_change_without_gate": multisig_signer_change_without_gate,
                    "multisig_threshold_change_without_validation": multisig_threshold_change_without_validation,
                    "multisig_signer_change_without_validation": multisig_signer_change_without_validation,
                    "is_multisig_threshold_change": is_multisig_threshold_change,
                    "is_multisig_member_change": is_multisig_member_change,
                    "multisig_member_change_without_minimum_check": multisig_member_change_without_minimum_check,
                    "multisig_threshold_change_without_owner_count_check": multisig_threshold_change_without_owner_count_check,
                    "governance_exec_without_timelock_check": governance_exec_without_timelock_check,
                    "governance_exec_without_quorum_check": governance_exec_without_quorum_check,
                    "governance_exec_without_vote_period_check": governance_exec_without_vote_period_check,
                    "uses_abi_decode": uses_abi_decode,
                    "has_abi_decode_guard": has_abi_decode_guard,
                    "uses_selfdestruct": uses_selfdestruct,
                    "uses_extcodesize": uses_extcodesize,
                    "uses_extcodehash": uses_extcodehash,
                    "uses_gasleft": uses_gasleft,
                    "uses_calldata_slice": uses_calldata_slice,
                    "has_calldata_length_check": has_calldata_length_check,
                    "allocates_memory_array_from_input": allocates_memory_array_from_input,
                    "recursive_call": recursive_call,
                    "calldata_slice_without_check": calldata_slice_without_check,
                    "recursive_call_without_guard": recursive_call_without_guard,
                    "uses_merkle_proof": uses_merkle_proof,
                    "merkle_leaf_domain_separated": merkle_leaf_domain_separated,
                    "address_parameter_used_for_transfer": address_parameter_used_for_transfer,
                    "address_parameter_used_for_call": address_parameter_used_for_call,
                    "validates_address_nonzero": validates_address_nonzero,
                    "validates_address_not_self": validates_address_not_self,
                    "validates_contract_code": validates_contract_code,
                    "has_fee_parameter": has_fee_parameter,
                    "has_fee_bounds": has_fee_bounds,
                    "has_amount_bounds": has_amount_bounds,
                    "has_amount_nonzero_check": has_amount_nonzero_check,
                    "uses_amount_division": uses_amount_division,
                    "uses_division": uses_division,
                    "divisor_source": divisor_source,
                    "divisor_validated_nonzero": divisor_validated_nonzero,
                    "uses_arithmetic": uses_arithmetic,
                    "uses_unchecked_block": uses_unchecked_block,
                    "uses_assert": uses_assert,
                    "has_precision_guard": has_precision_guard,
                    "has_array_length_check": has_array_length_check,
                    "has_array_length_match": has_array_length_match,
                    "has_array_index_check": has_array_index_check,
                    "has_multi_array_parameter": has_multi_array_parameter,
                    "has_oracle_aggregation_sanity": has_oracle_aggregation_sanity,
                    "has_oracle_decimals_normalized": has_oracle_decimals_normalized,
                    "has_oracle_min_source_count": has_oracle_min_source_count,
                    "has_oracle_per_source_staleness": has_oracle_per_source_staleness,
                    "has_oracle_time_alignment": has_oracle_time_alignment,
                    "has_oracle_weighted_aggregation": has_oracle_weighted_aggregation,
                    "has_oracle_circuit_breaker": has_oracle_circuit_breaker,
                    "has_oracle_disagreement_fallback": has_oracle_disagreement_fallback,
                    "has_oracle_min_agreement": has_oracle_min_agreement,
                    "has_oracle_source_health_check": has_oracle_source_health_check,
                    "has_oracle_update_frequency_alignment": has_oracle_update_frequency_alignment,
                    "oracle_update_function": oracle_update_function,
                    "has_oracle_update_rate_limit": has_oracle_update_rate_limit,
                    "has_oracle_update_timelock": has_oracle_update_timelock,
                    "has_oracle_update_deviation_check": has_oracle_update_deviation_check,
                    "has_oracle_update_signature_check": has_oracle_update_signature_check,
                    "has_oracle_update_sequence_check": has_oracle_update_sequence_check,
                    "has_oracle_update_timestamp_check": has_oracle_update_timestamp_check,
                    "has_cross_chain_context": has_cross_chain_context,
                    "has_cross_chain_validation": has_cross_chain_validation,
                    "has_bridge_replay_protection": has_bridge_replay_protection,
                    "has_cross_chain_consistency_check": has_cross_chain_consistency_check,
                    "has_bridge_finality_check": has_bridge_finality_check,
                    "has_bridge_source_chain_check": has_bridge_source_chain_check,
                    "has_bridge_ordering_check": has_bridge_ordering_check,
                    "uses_fixed_oracle_decimals": uses_fixed_oracle_decimals,
                    "has_external_data_integrity_check": has_external_data_integrity_check,
                    "reads_balance_state": reads_balance_state,
                    "writes_balance_state": writes_balance_state,
                    "reads_share_state": reads_share_state,
                    "reads_supply_state": reads_supply_state,
                    "writes_supply_state": writes_supply_state,
                    "reads_dependency_state": reads_dependency_state,
                    "contract_has_inheritance": contract_has_inheritance,
                    "contract_has_composition": contract_has_composition,
                    "calls_external_contract": calls_external_contract,
                    "external_call_contracts": sorted(external_call_contracts),
                    "callback_chain_surface": callback_chain_surface,
                    "protocol_callback_chain_surface": protocol_callback_chain_surface,
                    "callback_entrypoint_surface": callback_entrypoint_surface,
                    "contract_has_balance_tracking": contract_has_balance_tracking,
                    "token_callback_surface": token_callback_surface,
                    "transfers_eth": transfers_eth,
                    "uses_fixed_gas_stipend": uses_fixed_gas_stipend,
                    "semgrep_like_rules": sorted(semgrep_rules),
                    "semgrep_like_count": len(semgrep_rules),
                    "semgrep_like_security_count": semgrep_security_count,
                    "has_unchecked_block": has_unchecked_block,
                    "unchecked_contains_arithmetic": unchecked_contains_arithmetic,
                    "unchecked_operand_from_user": unchecked_operand_from_user,
                    "unchecked_affects_balance": unchecked_affects_balance,
                    "has_arithmetic": has_arithmetic,
                    "has_division": has_division,
                    "has_multiplication": has_multiplication,
                    "division_before_multiplication": division_before_multiplication,
                    "in_financial_context": in_financial_context,
                    "has_explicit_cast": has_explicit_cast,
                    "cast_is_narrowing": cast_is_narrowing,
                    "has_bounds_check_before_cast": has_bounds_check_before_cast,
                    "has_signed_to_unsigned_cast": has_signed_to_unsigned_cast,
                    "has_signed_check": has_signed_check,
                    "has_address_to_uint_cast": has_address_to_uint_cast,
                    "divisor_validated_nonzero": divisor_validated_nonzero,
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
                    "loop_counter_small_type": loop_counter_small_type,
                    "pre_08_arithmetic": pre_08_arithmetic,
                    "division_precision_risk": division_precision_risk,
                    "fee_precision_risk": fee_precision_risk,
                    "basis_points_precision_risk": basis_points_precision_risk,
                    "ratio_calculation_risk": ratio_calculation_risk,
                    "price_amount_overflow_risk": price_amount_overflow_risk,
                    "percentage_overflow_risk": percentage_overflow_risk,
                    "token_decimal_mismatch": token_decimal_mismatch,
                    "unchecked_arithmetic_risk": unchecked_arithmetic_risk,
                    "division_by_zero_risk": division_by_zero_risk,
                    "signed_unsigned_cast_risk": signed_unsigned_cast_risk,
                    "narrowing_cast_risk": narrowing_cast_risk,
                    "multiplication_overflow_risk": multiplication_overflow_risk,
                    "fee_accumulation_overflow_risk": fee_accumulation_overflow_risk,
                    "writes_share_state": writes_share_state,
                    "writes_collateral_state": writes_collateral_state,
                    "writes_pool_state": writes_pool_state,
                    "modifies_state_machine_variable": modifies_state_machine_variable,
                    "state_variable_is_state_machine": modifies_state_machine_variable,
                    "modifies_state_variable": bool(writes_state),
                    "validates_current_state": validates_current_state,
                    "enforces_valid_transition": enforces_valid_transition,
                    "allows_invalid_transition": allows_invalid_transition,
                    "state_cleanup_missing": state_cleanup_missing,
                    "state_race_condition": state_race_condition,
                    "accounting_update_missing": accounting_update_missing,
                    "double_counting_risk": double_counting_risk,
                    "rounding_accumulation_risk": rounding_accumulation_risk,
                    "emits_event": emits_event,
                    "event_param_mismatch": event_param_mismatch,
                    "override_missing_super": override_missing_super,
                    "selfdestruct_target_user_controlled": selfdestruct_target_user_controlled,
                    "extcodesize_in_constructor": extcodesize_in_constructor,
                    "share_inflation_risk": share_inflation_risk,
                    "missing_return_value_check": missing_return_value_check,
                    "missing_amount_bounds": missing_amount_bounds,
                    "modifies_balance_state": writes_balance_state,
                    "maintains_balance_invariant": False,
                    "file": file_path,
                    "line_start": line_start,
                    "line_end": line_end,
                    # Phase 1-2: Semantic Operations & Sequencing
                    "semantic_ops": semantic_op_names,
                    "op_sequence": op_sequence,
                    "behavioral_signature": behavioral_signature,
                    "op_ordering": op_ordering,
                },
                evidence=self._evidence(file_path, line_start, line_end),
            )
            graph.add_node(node)
            graph.add_edge(
                Edge(
                    id=self._edge_id("CONTAINS_FUNCTION", contract_node.id, node_id),
                    type="CONTAINS_FUNCTION",
                    source=contract_node.id,
                    target=node_id,
                    evidence=self._evidence(file_path, line_start, line_end),
                )
            )
            self._link_modifiers(graph, fn, node)
            self._link_state_vars(graph, fn, node, contract)
            self._link_calls(graph, fn, node)
            self._link_external_callsites(graph, fn, node)
            self._link_signature_use(
                graph,
                fn_node=node,
                uses_ecrecover=uses_ecrecover,
                uses_chainid=uses_chainid,
                has_nonce_parameter=has_nonce_parameter,
            )
            self._link_loops(graph, node, loop_nodes)
            self._augment_taint(graph, fn, contract, node, input_sources, special_sources)

    def _annotate_cross_function_signals(self, graph: KnowledgeGraph, contract: Any) -> None:
        records: list[dict[str, Any]] = []
        for fn in getattr(contract, "functions", []) or []:
            file_path, line_start, _line_end = self._source_location(fn)
            label = self._function_label(fn)
            node_id = self._node_id("function", f"{contract.name}.{label}", file_path, line_start)
            node = graph.nodes.get(node_id)
            if node is None:
                continue
            reads_state = {getattr(var, "name", None) for var in getattr(fn, "state_variables_read", []) or []}
            writes_state = {getattr(var, "name", None) for var in getattr(fn, "state_variables_written", []) or []}
            reads_state.discard(None)
            writes_state.discard(None)
            writes_state_after_call = self._state_vars_written_after_external_call(fn)
            modifiers = [m.name for m in getattr(fn, "modifiers", []) if getattr(m, "name", None)]
            require_exprs = self._require_expressions(fn)
            has_reentrancy_guard = self._has_reentrancy_guard(modifiers, require_exprs)
            call_order = self._infer_call_order(fn)
            external_calls = getattr(fn, "external_calls", []) or []
            low_level_calls = getattr(fn, "low_level_calls", []) or []
            high_level_calls = getattr(fn, "high_level_calls", []) or []
            has_external_calls = bool(external_calls) or bool(low_level_calls) or bool(high_level_calls)
            records.append(
                {
                    "node": node,
                    "reads_state": reads_state,
                    "writes_state": writes_state,
                    "writes_state_after_call": writes_state_after_call,
                    "has_external_calls": has_external_calls,
                    "state_write_after_external_call": call_order.get("write_after_call", False),
                    "has_reentrancy_guard": has_reentrancy_guard,
                    "visibility": getattr(fn, "visibility", None),
                    "state_mutability": self._normalize_state_mutability(fn),
                }
            )

        vars_written_after_call: set[str] = set()
        for record in records:
            if record["has_external_calls"] and record["state_write_after_external_call"]:
                vars_written_after_call.update(record["writes_state_after_call"])

        for record in records:
            node = record["node"]
            node.properties.setdefault("cross_function_reentrancy_read", False)
            is_view = record["state_mutability"] == "view"
            if is_view and record["reads_state"] & vars_written_after_call:
                node.properties["read_only_reentrancy_surface"] = True
            else:
                node.properties.setdefault("read_only_reentrancy_surface", False)

        for record in records:
            if not (record["has_external_calls"] and record["state_write_after_external_call"]):
                record["node"].properties.setdefault("cross_function_reentrancy_surface", False)
                continue
            shared_state = record["writes_state_after_call"]
            vulnerable = False
            for candidate in records:
                if candidate is record:
                    continue
                if candidate["visibility"] not in {"public", "external"}:
                    continue
                if candidate["has_reentrancy_guard"]:
                    continue
                if shared_state & candidate["reads_state"]:
                    vulnerable = True
                    candidate["node"].properties["cross_function_reentrancy_read"] = True
            record["node"].properties["cross_function_reentrancy_surface"] = vulnerable

        has_shared_state = any(
            node.properties.get("cross_function_reentrancy_surface")
            for node in (record["node"] for record in records)
        )
        if not has_shared_state:
            for record in records:
                if not (record["has_external_calls"] and record["writes_state"]):
                    continue
                shared_state = record["writes_state"]
                for candidate in records:
                    if candidate is record:
                        continue
                    if candidate["visibility"] not in {"public", "external"}:
                        continue
                    if shared_state & candidate["reads_state"]:
                        has_shared_state = True
                        break
                if has_shared_state:
                    break
        contract_file, contract_line, _contract_end = self._source_location(contract)
        contract_id = self._node_id("contract", contract.name, contract_file, contract_line)
        contract_node = graph.nodes.get(contract_id)
        if contract_node is not None:
            contract_node.properties["has_functions_sharing_state"] = has_shared_state

    def _function_label(self, fn: Any) -> str:
        return getattr(fn, "full_name", None) or getattr(fn, "name", None) or "function"

    def _is_access_gate(self, modifier_name: str) -> bool:
        lowered = modifier_name.lower()
        keywords = ("only", "auth", "role", "admin", "owner", "guardian", "governor")
        return any(key in lowered for key in keywords)

    def _uses_var_name(self, variables: list[Any], name: str) -> bool:
        for var in variables:
            var_name = getattr(var, "name", None)
            if var_name == name:
                return True
            if name in str(var):
                return True
        return False

    def _classify_state_write_targets(self, state_vars: list[Any]) -> dict[str, list[str]]:
        targets: dict[str, list[str]] = {}
        for var in state_vars:
            name = getattr(var, "name", None) or ""
            if not name:
                continue
            tags = classify_state_var_name(name)
            targets[name] = tags
        return targets

    def _classify_state_read_targets(self, state_vars: list[Any]) -> dict[str, list[str]]:
        targets: dict[str, list[str]] = {}
        for var in state_vars:
            name = getattr(var, "name", None) or ""
            if not name:
                continue
            tags = classify_state_var_name(name)
            targets[name] = tags
        return targets

    def _has_state_tag(self, targets: dict[str, list[str]], tag: str) -> bool:
        return any(tag in tags for tags in targets.values())

    def _contract_has_balance_tracking(self, contract: Any) -> bool:
        for var in getattr(contract, "state_variables", []) or []:
            tags = classify_state_var_name(getattr(var, "name", "") or "")
            if "balance" in tags or "shares" in tags:
                return True
        return False

    def _contract_has_composition(self, contract: Any) -> bool:
        for var in getattr(contract, "state_variables", []) or []:
            tags = classify_state_var_name(getattr(var, "name", "") or "")
            if "dependency" in tags:
                return True
        return False

    def _summarize_low_level_calls(
        self,
        low_level_calls: list[Any],
        parameter_names: list[str],
        require_exprs: list[str],
        nodes: list[Any],
    ) -> dict[str, bool | int]:
        has_call_with_value = False
        has_call_with_gas = False
        has_hardcoded_gas = False
        call_target_user_controlled = False
        call_data_user_controlled = False
        call_value_user_controlled = False
        delegatecall_target_user_controlled = False
        for call in low_level_calls:
            call_value = getattr(call, "call_value", None)
            call_gas = getattr(call, "call_gas", None)
            if call_value is not None:
                has_call_with_value = True
                if self._is_user_controlled_expression(call_value, parameter_names, allow_msg_value=True):
                    call_value_user_controlled = True
            if call_gas is not None:
                has_call_with_gas = True
                if self._is_hardcoded_gas(call_gas):
                    has_hardcoded_gas = True

            destination = self._callsite_destination(call)
            if destination and self._is_user_controlled_destination(destination, parameter_names):
                call_target_user_controlled = True
                raw_name = getattr(call, "function_name", None) or getattr(call, "name", "") or ""
                if "delegatecall" in str(raw_name).lower():
                    delegatecall_target_user_controlled = True

            call_data = self._callsite_data_expression(call)
            if call_data and self._is_user_controlled_expression(call_data, parameter_names, allow_msg_value=False):
                call_data_user_controlled = True

        return {
            "has_low_level_calls": bool(low_level_calls),
            "low_level_call_count": len(low_level_calls),
            "has_call_with_value": has_call_with_value,
            "has_call_with_gas": has_call_with_gas,
            "has_hardcoded_gas": has_hardcoded_gas,
            "call_target_user_controlled": call_target_user_controlled,
            "call_data_user_controlled": call_data_user_controlled,
            "call_value_user_controlled": call_value_user_controlled,
            "checks_low_level_call_success": self._checks_low_level_call_success(require_exprs),
            "decodes_call_return": self._decodes_call_return(nodes),
            "checks_returndata_length": self._checks_returndata_length(require_exprs),
            "delegatecall_target_user_controlled": delegatecall_target_user_controlled,
        }

    def _external_call_target_user_controlled(
        self,
        external_calls: list[Any],
        high_level_calls: list[Any],
        parameter_names: list[str],
    ) -> bool:
        for call in external_calls:
            destination = self._callsite_destination(call)
            if destination and self._is_user_controlled_destination(destination, parameter_names):
                return True
            expression = getattr(call, "expression", None)
            if expression is not None and self._is_user_controlled_expression(
                expression, parameter_names, allow_msg_value=False
            ):
                return True
        for _, call in high_level_calls:
            destination = self._callsite_destination(call)
            if destination and self._is_user_controlled_destination(destination, parameter_names):
                return True
            expression = getattr(call, "expression", None)
            if expression is not None and self._is_user_controlled_expression(
                expression, parameter_names, allow_msg_value=False
            ):
                return True
        return False

    def _owner_is_single_address(self, state_vars: list[Any]) -> bool:
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
            if text in {"address(0)", "0x0", "0x0000000000000000000000000000000000000000", "0"}:
                return True
        return False

    def _summarize_contract_privilege(self, contract: Any) -> dict[str, bool]:
        has_unprotected = False
        has_protected = False
        has_privileged = False
        for fn in getattr(contract, "functions", []) or []:
            modifiers = [m.name for m in getattr(fn, "modifiers", []) if getattr(m, "name", None)]
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

    def _has_initializer_modifier(self, modifiers: list[str]) -> bool:
        for modifier in modifiers:
            lowered = modifier.lower()
            if "initializer" in lowered or "reinitializer" in lowered:
                return True
        return False

    def _has_only_proxy_modifier(self, modifiers: list[str]) -> bool:
        for modifier in modifiers:
            lowered = modifier.lower()
            if "onlyproxy" in lowered or "onlydelegatecall" in lowered or "onlydelegated" in lowered:
                return True
        return False

    def _has_only_proxy_modifier(self, modifiers: list[str]) -> bool:
        for modifier in modifiers:
            if "onlyproxy" in modifier.lower():
                return True
        return False

    def _checks_initialized_flag(self, require_exprs: list[str]) -> bool:
        for expr in require_exprs:
            lowered = expr.lower()
            if "initialized" not in lowered and "init" not in lowered:
                continue
            if "!" in lowered or "== false" in lowered or "==0" in lowered:
                return True
        return False

    def _tx_origin_in_require(self, require_exprs: list[str]) -> bool:
        for expr in require_exprs:
            lowered = expr.lower()
            if "tx.origin" in lowered:
                return True
        return False

    def _access_gate_uses_or(self, require_exprs: list[str]) -> bool:
        for expr in require_exprs:
            lowered = expr.lower()
            if not any(token in lowered for token in ("msg.sender", "owner", "admin", "role")):
                continue
            if "||" in lowered or " or " in lowered:
                return True
        return False

    def _has_block_timestamp_check(self, require_exprs: list[str]) -> bool:
        for expr in require_exprs:
            lowered = expr.lower()
            if "block.timestamp" not in lowered:
                continue
            if any(op in lowered for op in ("<=", ">=", "<", ">", "==")):
                return True
        return False

    def _has_timelock_parameter(self, parameter_names: list[str]) -> bool:
        tokens = ("timelock", "delay", "eta", "executeafter", "unlock", "cooldown")
        return any(any(token in name.lower() for token in tokens) for name in parameter_names)

    def _has_timelock_check(
        self, require_exprs: list[str], parameter_names: list[str]
    ) -> bool:
        tokens = ("timelock", "delay", "eta", "executeafter", "unlock", "cooldown")
        candidate_params = {name for name in parameter_names if any(token in name.lower() for token in tokens)}
        for expr in require_exprs:
            lowered = expr.lower()
            if "block.timestamp" not in lowered:
                continue
            if not candidate_params:
                if any(token in lowered for token in tokens):
                    return True
                continue
            if any(name in lowered for name in candidate_params):
                return True
        return False

    def _validates_delegatecall_target(
        self, require_exprs: list[str], parameter_names: list[str]
    ) -> bool:
        target_params = {name.lower() for name in parameter_names if "target" in name.lower()}
        tokens = target_params | {"implementation", "impl", "logic", "whitelist", "allowlist"}
        for expr in require_exprs:
            lowered = expr.lower()
            if "delegatecall" in lowered:
                continue
            if not any(token in lowered for token in tokens):
                continue
            if "==" in lowered or "!=" in lowered or "contains" in lowered:
                return True
        return False

    def _validates_call_target(
        self, require_exprs: list[str], address_param_names: list[str]
    ) -> bool:
        if not address_param_names:
            return False
        allowlist_tokens = (
            "allow",
            "whitelist",
            "approved",
            "trusted",
            "registry",
            "authorized",
            "permitted",
        )
        for expr in require_exprs:
            lowered = expr.lower()
            if not any(name.lower() in lowered for name in address_param_names):
                continue
            if any(token in lowered for token in allowlist_tokens):
                return True
            if "==" in lowered and any(token in lowered for token in ("owner", "admin", "guardian", "governor")):
                return True
            if "==" in lowered and "address(" in lowered:
                return True
        return False

    def _is_admin_named_function(self, label: str) -> bool:
        name = (label or "").split("(")[0].lower()
        if not name:
            return False
        prefixes = (
            "set",
            "update",
            "configure",
            "change",
            "modify",
            "grant",
            "revoke",
            "add",
            "remove",
            "pause",
            "unpause",
            "upgrade",
            "migrate",
            "rescue",
            "recover",
            "emergency",
            "force",
        )
        if any(name.startswith(prefix) for prefix in prefixes):
            return True
        return any(token in name for token in ("admin", "owner", "guardian"))

    def _is_emergency_function(self, label: str) -> bool:
        name = (label or "").split("(")[0].lower()
        return any(token in name for token in ("emergency", "rescue", "recover"))

    def _is_timelock_admin_function(self, label: str) -> bool:
        name = (label or "").split("(")[0].lower()
        if "timelock" not in name:
            return False
        return any(token in name for token in ("admin", "owner", "guardian", "controller", "manager", "set"))

    def _has_role_enumeration(self, state_vars: list[Any]) -> bool:
        for var in state_vars:
            name = (getattr(var, "name", "") or "").lower()
            if not name:
                continue
            if any(token in name for token in ("member", "members", "enumerable", "rolelist", "role_list", "roleset")):
                return True
        return False

    def _has_role_events(self, contract: Any) -> bool:
        for event in getattr(contract, "events", []) or []:
            name = (getattr(event, "name", "") or "").lower()
            if any(token in name for token in ("role", "grant", "revoke", "admin")):
                return True
        return False

    def _has_governance_signals(self, state_vars: list[Any], function_names: list[str]) -> bool:
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

    def _modifies_roles(self, state_write_targets: dict[str, list[str]], label: str) -> bool:
        for tags in state_write_targets.values():
            if "role" in tags or "owner" in tags:
                return True
        label_lower = (label or "").lower()
        return any(
            token in label_lower
            for token in ("grant", "revoke", "role", "admin", "owner", "setrole", "addrole", "removerole")
        )

    def _is_callback_function(self, fn: Any) -> bool:
        if getattr(fn, "is_fallback", False) or getattr(fn, "is_receive", False):
            return True
        name = (getattr(fn, "name", "") or "").lower()
        return name.startswith("on") or "callback" in name or "hook" in name

    def _infer_call_order(self, fn: Any) -> dict[str, bool]:
        nodes = getattr(fn, "nodes", []) or []
        write_before = False
        write_after = False
        seen_call = False
        for node in nodes:
            if self._node_has_external_call(node):
                seen_call = True
            if getattr(node, "state_variables_written", []) or []:
                if seen_call:
                    write_after = True
                else:
                    write_before = True
            if write_before and write_after:
                break
        return {"write_before_call": write_before, "write_after_call": write_after}

    def _state_vars_written_after_external_call(self, fn: Any) -> set[str]:
        nodes = getattr(fn, "nodes", []) or []
        seen_call = False
        written: set[str] = set()
        for node in nodes:
            if self._node_has_external_call(node):
                seen_call = True
            if not seen_call:
                continue
            for var in getattr(node, "state_variables_written", []) or []:
                name = getattr(var, "name", None)
                if name:
                    written.add(name)
        return written

    def _node_has_external_call(self, node: Any) -> bool:
        for ir in getattr(node, "irs", []) or []:
            name = type(ir).__name__
            if name in {"LowLevelCall", "HighLevelCall", "ExternalCall"}:
                return True
        return False

    def _node_type_name(self, node: Any) -> str:
        node_type = getattr(node, "type", None)
        name = getattr(node_type, "name", None)
        if name:
            return str(name).lower()
        return str(node_type).lower()

    def _is_loop_start(self, node: Any) -> bool:
        name = self._node_type_name(node)
        return "startloop" in name or "loopstart" in name

    def _is_loop_end(self, node: Any) -> bool:
        name = self._node_type_name(node)
        return "endloop" in name or "loopend" in name

    def _node_has_delete(self, node: Any) -> bool:
        expression = self._node_expression(node)
        if "delete" in expression.lower():
            return True
        for ir in getattr(node, "irs", []) or []:
            ir_name = type(ir).__name__.lower()
            if "delete" in ir_name or "delete" in str(ir).lower():
                return True
        return False

    def _node_expression(self, node: Any) -> str:
        expression = getattr(node, "expression", None)
        if expression is None:
            return ""
        return str(expression)

    def _callsite_data_expression(self, call: Any) -> str:
        for attr in ("call_data", "data", "arguments", "args"):
            value = getattr(call, attr, None)
            if value is not None:
                if isinstance(value, list):
                    names = []
                    for item in value:
                        name = getattr(item, "name", None)
                        if name:
                            names.append(name)
                    if names:
                        return " ".join(names)
                return str(value)
        expression = getattr(call, "expression", None)
        if expression is not None:
            return str(expression)
        return str(call)

    def _is_user_controlled_destination(self, destination: str, parameter_names: list[str]) -> bool:
        lowered = destination.lower()
        if "msg.sender" in lowered or "tx.origin" in lowered:
            return True
        return any(name.lower() == lowered or name.lower() in lowered for name in parameter_names)

    def _is_user_controlled_expression(
        self,
        expression: Any,
        parameter_names: list[str],
        *,
        allow_msg_value: bool,
    ) -> bool:
        if isinstance(expression, list):
            for item in expression:
                name = getattr(item, "name", None)
                if name and any(param.lower() == name.lower() for param in parameter_names):
                    return True
            text = " ".join(str(item) for item in expression).lower()
        else:
            text = str(expression).lower()
        if allow_msg_value and "msg.value" in text:
            return True
        if "msg.sender" in text or "tx.origin" in text:
            return True
        return any(name.lower() in text for name in parameter_names)

    def _is_hardcoded_gas(self, gas_value: Any) -> bool:
        text = str(gas_value).strip().lower()
        return bool(re.fullmatch(r"0x[0-9a-f]+|\d+", text))

    def _checks_low_level_call_success(self, require_exprs: list[str]) -> bool:
        for expr in require_exprs:
            lowered = expr.lower()
            if "require" not in lowered:
                continue
            if any(token in lowered for token in ("success", "ok", "call")):
                return True
        return False

    def _decodes_call_return(self, nodes: list[Any]) -> bool:
        for node in nodes:
            expression = self._node_expression(node).lower()
            if "abi.decode" in expression or "returndata" in expression:
                return True
            for ir in getattr(node, "irs", []) or []:
                if "abi.decode" in str(ir).lower():
                    return True
        return False

    def _checks_returndata_length(self, require_exprs: list[str]) -> bool:
        for expr in require_exprs:
            lowered = expr.lower()
            if ".length" in lowered and ("data" in lowered or "returndata" in lowered):
                return True
        return False

    def _loop_bound_sources(
        self, node: Any, parameter_names: list[str], state_vars: list[Any]
    ) -> list[str]:
        expr = self._node_expression(node)
        if not expr:
            return ["unknown"]
        lowered = expr.lower()
        sources: set[str] = set()
        if any(name.lower() in lowered for name in parameter_names):
            sources.add("user_input")
        if ".length" in lowered:
            sources.add("storage_length")
        for var in state_vars:
            name = getattr(var, "name", None)
            if not name:
                continue
            if f"{name.lower()}.length" in lowered:
                sources.add("storage_length")
        if re.search(r"\b\d+\b", lowered):
            sources.add("constant")
        if not sources:
            sources.add("unknown")
        return sorted(sources)

    def _analyze_loops(
        self, fn: Any, parameter_names: list[str], state_vars: list[Any]
    ) -> tuple[dict[str, Any], list[dict[str, Any]]]:
        nodes = getattr(fn, "nodes", []) or []
        loops: list[dict[str, Any]] = []
        loop_stack: list[dict[str, Any]] = []
        max_depth = 0
        for node in nodes:
            node_type = self._node_type_name(node)
            is_start = self._is_loop_start(node)
            is_end = self._is_loop_end(node)
            is_loop_marker = "loop" in node_type
            expression = self._node_expression(node)

            if (is_start or (is_loop_marker and not loop_stack and not is_end)) and expression:
                bound_sources = self._loop_bound_sources(node, parameter_names, state_vars)
                file_path, line_start, line_end = self._source_location(
                    getattr(node, "expression", node)
                )
                loop_info = {
                    "index": len(loops),
                    "bound_sources": bound_sources,
                    "file": file_path,
                    "line_start": line_start,
                    "line_end": line_end,
                    "has_external_call": False,
                    "has_delete": False,
                }
                loops.append(loop_info)
                loop_stack.append(loop_info)
                max_depth = max(max_depth, len(loop_stack))
            elif loop_stack and is_loop_marker and not is_end:
                bound_sources = self._loop_bound_sources(node, parameter_names, state_vars)
                current = loop_stack[-1]
                merged = set(current["bound_sources"])
                if not (bound_sources == ["unknown"] and merged):
                    merged.update(bound_sources)
                current["bound_sources"] = sorted(merged)

            if loop_stack and self._node_has_external_call(node):
                for loop_info in loop_stack:
                    loop_info["has_external_call"] = True
            if loop_stack and self._node_has_delete(node):
                for loop_info in loop_stack:
                    loop_info["has_delete"] = True

            if is_end and loop_stack:
                loop_stack.pop()

        bound_sources = sorted({src for loop in loops for src in loop["bound_sources"]})
        bounded_tokens = {"constant"}  # Fixed: storage_length is unbounded (arrays grow via push())
        unbounded_tokens = {"user_input", "unknown", "storage_length"}
        has_unbounded_loop = any(
            (set(loop["bound_sources"]) & unbounded_tokens)
            and not (set(loop["bound_sources"]) & bounded_tokens)
            for loop in loops
        )
        has_external_calls_in_loop = any(loop["has_external_call"] for loop in loops)
        has_delete_in_loop = any(loop["has_delete"] for loop in loops)
        has_unbounded_deletion = any(
            loop["has_delete"]
            and (set(loop["bound_sources"]) & unbounded_tokens)
            and not (set(loop["bound_sources"]) & bounded_tokens)
            for loop in loops
        )
        summary = {
            "has_loops": bool(loops),
            "loop_count": len(loops),
            "max_loop_depth": max_depth,
            "has_nested_loop": max_depth >= 2,
            "loop_bound_sources": bound_sources,
            "has_unbounded_loop": has_unbounded_loop,
            "external_calls_in_loop": has_external_calls_in_loop,
            "has_delete_in_loop": has_delete_in_loop,
            "has_unbounded_deletion": has_unbounded_deletion,
        }
        return summary, loops

    def _link_loops(self, graph: KnowledgeGraph, fn_node: Node, loops: list[dict[str, Any]]) -> None:
        for loop_info in loops:
            file_path = loop_info["file"]
            line_start = loop_info["line_start"]
            line_end = loop_info["line_end"]
            node_id = self._node_id("loop", f"{fn_node.id}:{loop_info['index']}", file_path, line_start)
            graph.add_node(
                Node(
                    id=node_id,
                    type="Loop",
                    label="loop",
                    properties={
                        "bound_sources": loop_info["bound_sources"],
                        "has_external_call": loop_info["has_external_call"],
                        "has_delete": loop_info["has_delete"],
                        "file": file_path,
                        "line_start": line_start,
                        "line_end": line_end,
                    },
                    evidence=self._evidence(file_path, line_start, line_end),
                )
            )
            graph.add_edge(
                Edge(
                    id=self._edge_id("FUNCTION_HAS_LOOP", fn_node.id, node_id),
                    type="FUNCTION_HAS_LOOP",
                    source=fn_node.id,
                    target=node_id,
                )
            )

    def _access_gate_from_predicates(self, fn: Any) -> tuple[bool, list[str]]:
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

    def _add_invariants(
        self, graph: KnowledgeGraph, contract: Any, contract_node: Node
    ) -> list[dict[str, Any]]:
        invariants = self._extract_invariants(contract)
        for invariant in invariants:
            node_id = invariant["id"]
            graph.add_node(
                Node(
                    id=node_id,
                    type="Invariant",
                    label=invariant["label"],
                    properties={
                        "text": invariant["text"],
                        "source_kind": invariant["source_kind"],
                        "target_type": invariant["target_type"],
                        "target_name": invariant["target_name"],
                        "state_vars": invariant["state_vars"],
                        "guard_functions": invariant.get("guard_functions", []),
                        "file": invariant["file"],
                        "line_start": invariant["line_start"],
                        "line_end": invariant["line_end"],
                    },
                    evidence=self._evidence(
                        invariant["file"], invariant["line_start"], invariant["line_end"]
                    ),
                )
            )
            if invariant["target_type"] == "Contract":
                graph.add_edge(
                    Edge(
                        id=self._edge_id("INVARIANT_TARGETS_CONTRACT", node_id, contract_node.id),
                        type="INVARIANT_TARGETS_CONTRACT",
                        source=node_id,
                        target=contract_node.id,
                    )
                )
            if invariant["target_type"] == "Function" and invariant.get("target_id"):
                graph.add_edge(
                    Edge(
                        id=self._edge_id("INVARIANT_TARGETS_FUNCTION", node_id, invariant["target_id"]),
                        type="INVARIANT_TARGETS_FUNCTION",
                        source=node_id,
                        target=invariant["target_id"],
                    )
                )
            for state_id in invariant.get("state_ids", []):
                graph.add_edge(
                    Edge(
                        id=self._edge_id("INVARIANT_TARGETS_STATE", node_id, state_id),
                        type="INVARIANT_TARGETS_STATE",
                        source=node_id,
                        target=state_id,
                    )
                )
        return invariants

    def _update_functions_for_invariants(
        self, graph: KnowledgeGraph, contract: Any, invariants: list[dict[str, Any]]
    ) -> None:
        if not invariants:
            return
        invariants_by_state: dict[str, set[str]] = {}
        invariant_guards: dict[str, list[str]] = {}
        for invariant in invariants:
            for state_var in invariant.get("state_vars", []):
                invariants_by_state.setdefault(state_var, set()).add(invariant["id"])
            invariant_guards[invariant["id"]] = invariant.get("guard_functions", [])

        for fn in getattr(contract, "functions", []):
            file_path, line_start, _line_end = self._source_location(fn)
            label = self._function_label(fn)
            node_id = self._node_id("function", f"{contract.name}.{label}", file_path, line_start)
            node = graph.nodes.get(node_id)
            if not node:
                continue

            touched_state_vars = {
                getattr(var, "name", None)
                for var in (getattr(fn, "state_variables_read", []) or [])
                + (getattr(fn, "state_variables_written", []) or [])
                if getattr(var, "name", None)
            }
            written_state_vars = {
                getattr(var, "name", None)
                for var in (getattr(fn, "state_variables_written", []) or [])
                if getattr(var, "name", None)
            }
            invariant_state_vars = sorted(
                {name for name in touched_state_vars if name in invariants_by_state}
            )
            invariant_written_vars = sorted(
                {name for name in written_state_vars if name in invariants_by_state}
            )
            touches_invariant = bool(invariant_state_vars)
            guard_functions = self._invariant_guard_functions(
                invariant_written_vars, invariants_by_state, invariant_guards
            )
            has_invariant_check = self._function_has_invariant_check(
                fn, invariant_state_vars, guard_functions
            )

            node.properties["touches_invariant"] = touches_invariant
            node.properties["has_invariant_check"] = has_invariant_check
            node.properties["touches_invariant_unchecked"] = (
                bool(invariant_written_vars) and not has_invariant_check
            )
            node.properties["invariant_state_vars"] = invariant_state_vars
            node.properties["maintains_balance_invariant"] = bool(
                has_invariant_check and node.properties.get("writes_balance_state")
            )

            if touches_invariant:
                for state_var in invariant_state_vars:
                    for invariant_id in sorted(invariants_by_state[state_var]):
                        graph.add_edge(
                            Edge(
                                id=self._edge_id("FUNCTION_TOUCHES_INVARIANT", node_id, invariant_id),
                                type="FUNCTION_TOUCHES_INVARIANT",
                                source=node_id,
                                target=invariant_id,
                            )
                        )

    def _invariant_guard_functions(
        self,
        invariant_state_vars: list[str],
        invariants_by_state: dict[str, set[str]],
        invariant_guards: dict[str, list[str]],
    ) -> set[str]:
        guard_functions: set[str] = set()
        for state_var in invariant_state_vars:
            for invariant_id in invariants_by_state.get(state_var, set()):
                for guard in invariant_guards.get(invariant_id, []):
                    if not guard:
                        continue
                    guard_functions.add(guard)
                    guard_functions.add(self._normalize_guard_name(guard))
        return guard_functions

    def _function_has_invariant_check(
        self,
        fn: Any,
        invariant_state_vars: list[str],
        guard_functions: set[str],
        visited: set[int] | None = None,
    ) -> bool:
        if visited is None:
            visited = set()
        fn_identity = id(fn)
        if fn_identity in visited:
            return False
        visited.add(fn_identity)

        if invariant_state_vars and self._expressions_reference_state_vars(
            self._require_expressions(fn), invariant_state_vars
        ):
            return True
        if guard_functions and self._calls_guard_function(fn, guard_functions):
            return True

        for modifier in getattr(fn, "modifiers", []) or []:
            modifier_name = getattr(modifier, "name", None)
            if modifier_name and modifier_name in guard_functions:
                return True
            if self._function_has_invariant_check(
                modifier, invariant_state_vars, guard_functions, visited
            ):
                return True

        for callee in self._internal_call_functions(fn):
            if self._function_has_invariant_check(
                callee, invariant_state_vars, guard_functions, visited
            ):
                return True
        return False

    def _expressions_reference_state_vars(
        self, expressions: list[str], invariant_state_vars: list[str]
    ) -> bool:
        if not expressions or not invariant_state_vars:
            return False
        invariant_tokens = {name.lower() for name in invariant_state_vars if name}
        for expr in expressions:
            tokens = {token.lower() for token in re.findall(r"[A-Za-z_][A-Za-z0-9_]*", expr)}
            if invariant_tokens & tokens:
                return True
        return False

    def _calls_guard_function(self, fn: Any, guard_functions: set[str]) -> bool:
        for call in self._internal_call_functions(fn):
            if self._function_name_matches(call, guard_functions):
                return True
        guard_names = {self._normalize_guard_name(name) for name in guard_functions}
        guard_names.discard("")
        for node in getattr(fn, "nodes", []) or []:
            expression = self._node_expression(node)
            for guard_name in guard_names:
                if f"{guard_name}(" in expression.replace(" ", ""):
                    return True
        return False

    def _function_name_matches(self, fn: Any, guard_functions: set[str]) -> bool:
        fn_name = getattr(fn, "name", None)
        fn_full = getattr(fn, "full_name", None)
        return bool(
            (fn_name and fn_name in guard_functions)
            or (fn_full and fn_full in guard_functions)
        )

    def _normalize_guard_name(self, guard_name: str) -> str:
        name = str(guard_name).strip()
        if "(" in name:
            name = name.split("(", 1)[0].strip()
        return name

    def _internal_call_functions(self, fn: Any) -> list[Any]:
        targets: list[Any] = []
        for call in getattr(fn, "internal_calls", []) or []:
            target = getattr(call, "function", None) or call
            if target is None:
                continue
            if getattr(target, "name", None) is None and getattr(target, "full_name", None) is None:
                continue
            targets.append(target)
        return targets

    def _extract_invariants(self, contract: Any) -> list[dict[str, Any]]:
        file_path, line_start, line_end = self._source_location(contract)
        if not file_path or file_path == "unknown":
            return []
        lines = self._source_lines(file_path)
        if not lines:
            return []

        state_vars = getattr(contract, "state_variables", []) or []
        functions = getattr(contract, "functions", []) or []
        state_var_names = [getattr(var, "name", None) for var in state_vars]
        state_var_names = [name for name in state_var_names if name]

        invariants: list[dict[str, Any]] = []
        contract_comment = self._invariant_comment_above(lines, line_start)
        if contract_comment:
            text, comment_start, comment_end = contract_comment
            invariants.append(
                self._build_invariant_entry(
                    text=text,
                    file_path=file_path,
                    line_start=comment_start,
                    line_end=comment_end,
                    target_type="Contract",
                    target_name=contract.name,
                    target_id=None,
                    state_var_names=state_var_names,
                )
            )

        invariants.extend(
            self._extract_invariants_from_config(
                contract=contract,
                state_var_names=state_var_names,
                state_vars=state_vars,
                functions=functions,
            )
        )

        for var in state_vars:
            var_file, var_line_start, _var_line_end = self._source_location(var)
            comment = self._invariant_comment_above(lines, var_line_start)
            if not comment:
                continue
            text, comment_start, comment_end = comment
            entry = self._build_invariant_entry(
                text=text,
                file_path=var_file,
                line_start=comment_start,
                line_end=comment_end,
                target_type="StateVariable",
                target_name=var.name,
                target_id=None,
                state_var_names=state_var_names,
            )
            if var.name not in entry["state_vars"]:
                entry["state_vars"].append(var.name)
                entry["state_vars"] = sorted(set(entry["state_vars"]))
            entry["state_ids"] = [self._node_id("state", f"{contract.name}.{var.name}", var_file, var_line_start)]
            invariants.append(entry)

        for fn in functions:
            fn_file, fn_line_start, _fn_line_end = self._source_location(fn)
            comment = self._invariant_comment_above(lines, fn_line_start)
            if not comment:
                continue
            text, comment_start, comment_end = comment
            label = self._function_label(fn)
            target_id = self._node_id("function", f"{contract.name}.{label}", fn_file, fn_line_start)
            invariants.append(
                self._build_invariant_entry(
                    text=text,
                    file_path=fn_file,
                    line_start=comment_start,
                    line_end=comment_end,
                    target_type="Function",
                    target_name=label,
                    target_id=target_id,
                    state_var_names=state_var_names,
                )
            )

        for invariant in invariants:
            state_ids = []
            for name in invariant.get("state_vars", []):
                if name not in state_var_names:
                    continue
                var_obj = next((var for var in state_vars if var.name == name), None)
                if not var_obj:
                    continue
                var_file, var_line_start, _var_line_end = self._source_location(var_obj)
                state_ids.append(
                    self._node_id("state", f"{contract.name}.{name}", var_file, var_line_start)
                )
            invariant["state_ids"] = sorted(set(state_ids + invariant.get("state_ids", [])))

        return invariants

    def _build_invariant_entry(
        self,
        *,
        text: str,
        file_path: str,
        line_start: int,
        line_end: int,
        target_type: str,
        target_name: str,
        target_id: str | None,
        state_var_names: list[str],
        source_kind: str = "natspec",
        guard_functions: list[str] | None = None,
    ) -> dict[str, Any]:
        state_vars = self._extract_invariant_state_vars(text, state_var_names)
        label = f"invariant:{target_name}"
        return {
            "id": self._node_id("invariant", f"{target_name}:{line_start}", file_path, line_start),
            "label": label,
            "text": text,
            "source_kind": source_kind,
            "target_type": target_type,
            "target_name": target_name,
            "target_id": target_id,
            "state_vars": state_vars,
            "state_ids": [],
            "guard_functions": guard_functions or [],
            "file": file_path,
            "line_start": line_start,
            "line_end": line_end,
        }

    def _extract_invariant_state_vars(self, text: str, state_var_names: list[str]) -> list[str]:
        expression = self._invariant_expression_text(text)
        identifiers = self._ast_identifiers_from_expression(expression)
        if identifiers is None:
            tokens = {token.lower() for token in re.findall(r"[A-Za-z_][A-Za-z0-9_]*", text)}
            matches = [name for name in state_var_names if name.lower() in tokens]
            return sorted(set(matches))
        matches = [name for name in state_var_names if name in identifiers]
        return sorted(set(matches))

    def _invariant_expression_text(self, text: str) -> str:
        match = re.search(r"invariant\s*[:\-]?\s*(.*)", text, re.IGNORECASE)
        if match:
            tail = match.group(1).strip()
            if tail:
                return tail
        return text.strip()

    def _ast_identifiers_from_expression(self, expression: str) -> set[str] | None:
        normalized = self._normalize_invariant_expression(expression)
        if not normalized:
            return None
        try:
            tree = ast.parse(normalized, mode="eval")
        except SyntaxError:
            return None

        identifiers: set[str] = set()

        class _Visitor(ast.NodeVisitor):
            def visit_Name(self, node: ast.Name) -> None:
                identifiers.add(node.id)

        _Visitor().visit(tree)
        return identifiers

    def _normalize_invariant_expression(self, expression: str) -> str:
        cleaned = expression.strip()
        if not cleaned:
            return ""
        if "?" in cleaned and ":" in cleaned:
            return ""
        cleaned = cleaned.replace("&&", " and ").replace("||", " or ")
        cleaned = re.sub(r"!(?!=)", " not ", cleaned)
        cleaned = re.sub(r"\btrue\b", "True", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\bfalse\b", "False", cleaned, flags=re.IGNORECASE)
        return cleaned

    def _extract_invariants_from_config(
        self,
        *,
        contract: Any,
        state_var_names: list[str],
        state_vars: list[Any],
        functions: list[Any],
    ) -> list[dict[str, Any]]:
        base_dir = self.project_root / "tests" / "specs" / "config"
        if not base_dir.exists():
            return []
        invariants: list[dict[str, Any]] = []
        function_lookup: dict[str, Any] = {}
        for fn in functions:
            name = getattr(fn, "name", None)
            full = getattr(fn, "full_name", None)
            if name:
                function_lookup[name] = fn
            if full:
                function_lookup[full] = fn
        state_var_lookup = {var.name: var for var in state_vars if getattr(var, "name", None)}
        for path in sorted(base_dir.glob("*")):
            if path.suffix not in {".yaml", ".yml", ".json"}:
                continue
            entries = self._load_invariant_config_file(path)
            if not entries:
                continue
            for entry in entries:
                contract_name = entry.get("contract")
                contracts = entry.get("contracts")
                if contract_name and contract_name != contract.name:
                    continue
                if contracts and contract.name not in contracts:
                    continue

                target_type = entry.get("target_type") or "Contract"
                target_name = entry.get("target_name") or contract.name
                if target_type == "Contract":
                    target_name = contract.name
                target_id = None
                if target_type == "Function":
                    fn = function_lookup.get(target_name)
                    if fn:
                        fn_file, fn_line_start, _fn_line_end = self._source_location(fn)
                        target_id = self._node_id(
                            "function",
                            f"{contract.name}.{self._function_label(fn)}",
                            fn_file,
                            fn_line_start,
                        )
                if target_type == "StateVariable":
                    var = state_var_lookup.get(target_name)
                    if var:
                        var_file, var_line_start, _var_line_end = self._source_location(var)
                        state_id = self._node_id(
                            "state", f"{contract.name}.{target_name}", var_file, var_line_start
                        )
                    else:
                        state_id = None
                else:
                    state_id = None

                text = entry.get("expression") or entry.get("text") or entry.get("invariant") or ""
                guard_functions = entry.get("guard_functions") or []
                if isinstance(guard_functions, str):
                    guard_functions = [guard_functions]
                file_path = self._relpath(str(path))
                invariants.append(
                    self._build_invariant_entry(
                        text=text,
                        file_path=file_path,
                        line_start=entry.get("_line_start") or 1,
                        line_end=entry.get("_line_end") or 1,
                        target_type=target_type,
                        target_name=target_name,
                        target_id=target_id,
                        state_var_names=state_var_names,
                        source_kind="config",
                        guard_functions=[str(name) for name in guard_functions if name],
                    )
                )
                if target_type == "StateVariable" and state_id:
                    invariants[-1]["state_ids"] = [state_id]
        return invariants

    def _load_invariant_config_file(self, path: Path) -> list[dict[str, Any]]:
        try:
            raw = path.read_text(encoding="utf-8")
        except Exception:
            return []
        data: Any
        try:
            if path.suffix in {".yaml", ".yml"}:
                data = yaml.safe_load(raw)
            else:
                data = json.loads(raw)
        except Exception:
            return []
        if data is None:
            return []
        entries = data.get("invariants") if isinstance(data, dict) else data
        if not isinstance(entries, list):
            return []
        normalized: list[dict[str, Any]] = []
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            normalized.append(entry)
        return normalized

    def _invariant_comment_above(
        self, lines: list[str], line_start: int | None
    ) -> tuple[str, int, int] | None:
        if line_start is None or line_start <= 0:
            return None
        if line_start - 1 >= len(lines):
            return None
        inline_line = lines[line_start - 1]
        inline_match = re.search(r"//.*invariant|/\*.*invariant", inline_line, re.IGNORECASE)
        if inline_match:
            return self._clean_comment_block([inline_line]), line_start, line_start

        comment_lines: list[tuple[int, str]] = []
        idx = line_start - 2
        while idx >= 0:
            stripped = lines[idx].strip()
            if not stripped:
                break
            if stripped.startswith(("//", "///", "*", "/*", "*/")):
                comment_lines.append((idx + 1, lines[idx]))
                idx -= 1
                continue
            break
        if not comment_lines:
            return None
        comment_lines.reverse()
        text = self._clean_comment_block([line for _ln, line in comment_lines])
        if "invariant" not in text.lower():
            return None
        start_line = comment_lines[0][0]
        end_line = comment_lines[-1][0]
        return text, start_line, end_line

    def _clean_comment_block(self, lines: list[str]) -> str:
        cleaned = []
        for line in lines:
            stripped = line.strip()
            for token in ("///", "//", "/*", "*/"):
                if stripped.startswith(token):
                    stripped = stripped[len(token) :].strip()
            if stripped.startswith("*"):
                stripped = stripped[1:].strip()
            cleaned.append(stripped)
        return " ".join(part for part in cleaned if part)

    def _source_lines(self, file_path: str) -> list[str]:
        cached = self._source_cache.get(file_path)
        if cached is not None:
            return cached
        path = Path(file_path)
        if not path.is_absolute():
            path = self.project_root / file_path
        try:
            text = path.read_text(encoding="utf-8")
        except Exception:
            self._source_cache[file_path] = []
            return []
        lines = text.splitlines()
        self._source_cache[file_path] = lines
        return lines

    def _source_slice(
        self, file_path: str | None, line_start: int | None, line_end: int | None
    ) -> str:
        if not file_path or line_start is None or line_end is None:
            return ""
        lines = self._source_lines(file_path)
        if not lines:
            return ""
        start = max(line_start - 1, 0)
        end = min(line_end, len(lines))
        return "\n".join(lines[start:end])

    def _function_source_text(self, file_path: str | None, line_start: int | None, line_end: int | None) -> str:
        return self._source_slice(file_path, line_start, line_end).lower()

    def _strip_comments(self, text: str) -> str:
        text = re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)
        text = re.sub(r"//.*", "", text)
        return text

    def _detect_proxy_type(self, contract: Any) -> str:
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
        name = (getattr(fn, "name", "") or "").lower()
        signature = getattr(fn, "signature", "") or ""
        if isinstance(signature, (list, tuple)):
            signature_text = " ".join(str(item) for item in signature)
        else:
            signature_text = str(signature)
        signature_text = signature_text.lower()
        tokens = ("upgrade", "setimplementation", "setbeacon", "upgradebeacon")
        return any(token in name for token in tokens) or any(token in signature_text for token in tokens)

    def _is_initializer_function(self, fn: Any) -> bool:
        name = (getattr(fn, "name", "") or "").lower()
        return "initialize" in name

    def _state_var_name_match(self, state_vars: list[Any], token: str) -> bool:
        token_lower = token.lower()
        for var in state_vars:
            name = getattr(var, "name", None)
            if not name:
                continue
            if token_lower in name.lower():
                return True
        return False

    def _has_deadline_check(self, require_exprs: list[str], parameter_names: list[str]) -> bool:
        if not parameter_names:
            return False
        deadline_names = {name for name in parameter_names if any(key in name.lower() for key in ("deadline", "expiry", "expiration"))}
        if not deadline_names:
            return False
        for expression in require_exprs:
            if "block.timestamp" not in expression:
                continue
            if any(name in expression for name in deadline_names):
                return True
        return False

    def _has_deadline_future_check(self, require_exprs: list[str], parameter_names: list[str]) -> bool:
        if not parameter_names:
            return False
        deadline_names = {
            name for name in parameter_names if any(key in name.lower() for key in ("deadline", "expiry", "expiration"))
        }
        if not deadline_names:
            return False
        for expression in require_exprs:
            lowered = expression.lower()
            if "block.timestamp" not in lowered:
                continue
            for name in deadline_names:
                name_lower = name.lower()
                if re.search(rf"block\.timestamp\s*(<=|<)\s*{re.escape(name_lower)}", lowered):
                    return True
                if re.search(rf"{re.escape(name_lower)}\s*(>=|>)\s*block\.timestamp", lowered):
                    return True
        return False

    def _has_deadline_min_buffer(self, require_exprs: list[str], parameter_names: list[str]) -> bool:
        if not parameter_names:
            return False
        deadline_names = {
            name for name in parameter_names if any(key in name.lower() for key in ("deadline", "expiry", "expiration"))
        }
        if not deadline_names:
            return False
        for expression in require_exprs:
            lowered = expression.lower()
            if "block.timestamp" not in lowered:
                continue
            if not any(name.lower() in lowered for name in deadline_names):
                continue
            if "+" in lowered or "buffer" in lowered or "min" in lowered:
                return True
        return False

    def _has_deadline_max(self, require_exprs: list[str], parameter_names: list[str]) -> bool:
        if not parameter_names:
            return False
        deadline_names = {
            name for name in parameter_names if any(key in name.lower() for key in ("deadline", "expiry", "expiration"))
        }
        if not deadline_names:
            return False
        for expression in require_exprs:
            lowered = expression.lower()
            if not any(name.lower() in lowered for name in deadline_names):
                continue
            if "block.timestamp" in lowered and any(op in lowered for op in ("<", "<=")):
                return True
        return False

    def _parameter_type_name(self, param: Any) -> str:
        type_name = getattr(param, "type", None)
        return str(type_name or "").lower()

    def _address_parameter_names(self, parameters: list[Any]) -> list[str]:
        names: list[str] = []
        for param in parameters:
            name = getattr(param, "name", None)
            if not name:
                continue
            type_name = self._parameter_type_name(param)
            if "address" in type_name:
                names.append(str(name))
        return names

    def _array_parameter_names(self, parameters: list[Any]) -> list[str]:
        names: list[str] = []
        for param in parameters:
            name = getattr(param, "name", None)
            if not name:
                continue
            type_name = self._parameter_type_name(param)
            if "[]" in type_name or "array" in type_name:
                names.append(str(name))
        return names

    def _amount_parameter_names(self, parameters: list[Any]) -> list[str]:
        tokens = ("amount", "value", "qty", "quantity", "price", "size", "shares", "fee", "rate")
        names: list[str] = []
        for param in parameters:
            name = getattr(param, "name", None)
            if not name:
                continue
            lowered = str(name).lower()
            if any(token in lowered for token in tokens):
                names.append(str(name))
                continue
        return names

    def _bytes_parameter_names(self, parameters: list[Any]) -> list[str]:
        names: list[str] = []
        for param in parameters:
            name = getattr(param, "name", None)
            if not name:
                continue
            type_name = self._parameter_type_name(param)
            if "bytes" in type_name:
                names.append(str(name))
        return names

    def _threshold_parameter_names(self, parameters: list[Any]) -> list[str]:
        tokens = ("threshold", "min", "max", "limit", "cap", "floor", "ratio")
        names: list[str] = []
        for param in parameters:
            name = getattr(param, "name", None)
            if not name:
                continue
            lowered = str(name).lower()
            if any(token in lowered for token in tokens):
                names.append(str(name))
        return names

    def _pagination_parameter_names(self, parameters: list[Any]) -> list[str]:
        tokens = ("offset", "limit", "cursor", "page", "start", "end", "skip")
        names: list[str] = []
        for param in parameters:
            name = getattr(param, "name", None)
            if not name:
                continue
            lowered = str(name).lower()
            if any(token in lowered for token in tokens):
                names.append(str(name))
        return names

    def _token_call_kinds(self, fn: Any) -> set[str]:
        kinds: set[str] = set()
        for _, call in getattr(fn, "high_level_calls", []) or []:
            name = getattr(call, "function_name", None)
            if name is None:
                continue
            kinds.add(str(name).lower())
        return kinds

    def _require_expressions(self, fn: Any) -> list[str]:
        expressions: list[str] = []
        for node in getattr(fn, "nodes", []) or []:
            for ir in getattr(node, "irs", []) or []:
                if type(ir).__name__ != "SolidityCall":
                    continue
                expression = str(getattr(ir, "expression", "")) or str(ir)
                if "require" in expression or "assert" in expression:
                    expressions.append(expression)
        return expressions

    def _checks_token_call_return(self, require_exprs: list[str]) -> bool:
        tokens = ("transfer(", "transferfrom(", "approve(", "safetransfer", "safeapprove")
        return any(any(token in expr.lower() for token in tokens) for expr in require_exprs)

    def _approves_infinite_amount(self, source_text_lower: str) -> bool:
        """Detect approve() calls with infinite/max amounts"""
        # Common infinite approval patterns
        infinite_patterns = [
            "type(uint256).max",  # Solidity type(uint256).max
            "type(uint).max",     # Alternative syntax
            "uint256.max",        # Shortened form
            "uint.max",          # Shortened form
            "2**256-1",          # Arithmetic max
            "2**256 - 1",        # With spaces
            "0xffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff",  # Hex max
            "~uint256(0)",       # Bitwise NOT
            "~uint(0)",          # Bitwise NOT alternative
        ]
        # Check if approve() is called with any infinite pattern
        for line in source_text_lower.splitlines():
            if "approve(" in line:
                # Check if this line contains any infinite amount pattern
                if any(pattern.lower() in line for pattern in infinite_patterns):
                    return True
        return False

    def _inherits_upgradeable_base(self, contract: Any) -> bool:
        """
        Detect if contract inherits from common upgradeable base contracts.

        This provides semantic detection of upgradeability beyond name-based heuristics.
        Common upgradeable bases from OpenZeppelin and other frameworks include:
        - Initializable (core upgradeable contract pattern)
        - UUPSUpgradeable (UUPS proxy pattern)
        - OwnableUpgradeable, AccessControlUpgradeable, etc.
        - Any contract with "Upgradeable" suffix (OpenZeppelin convention)
        """
        upgradeable_base_patterns = [
            "initializable",           # OpenZeppelin Initializable.sol
            "uupsupgradeable",        # UUPS proxy pattern
            "upgradeable",            # Generic upgradeable suffix (OwnableUpgradeable, etc.)
            "transparentupgradeable", # Transparent proxy pattern
            "beaconupgradeable",      # Beacon proxy pattern
            "upgradeableproxy",       # Proxy variants
            "proxyupgradeable",
        ]

        bases = getattr(contract, "inheritance", []) or []
        for base in bases:
            base_name = getattr(base, "name", "").lower()
            if any(pattern in base_name for pattern in upgradeable_base_patterns):
                return True

        return False

    def _has_upgrade_pattern(self, function_names: list) -> bool:
        """
        Detect specific upgrade function patterns used in proxy implementations.

        This detects semantic upgrade patterns beyond just functions starting with "upgrade":
        - upgradeToAndCall (UUPS standard)
        - _authorizeUpgrade (UUPS access control)
        - upgradeTo (basic upgrade)
        - upgradeAndCall (with initialization)
        - setImplementation (proxy admin pattern)
        """
        upgrade_function_patterns = [
            "upgradetoandcall",    # UUPS standard upgrade function
            "_authorizeupgrade",   # UUPS access control hook
            "upgradeto",           # Basic upgrade function
            "upgradeandcall",      # Upgrade with initialization
            "setimplementation",   # Proxy admin pattern
            "_upgradeimplementation", # Internal upgrade helper
            "upgradebeacon",       # Beacon proxy upgrade
        ]

        lowered_names = [name.lower() for name in function_names]
        return any(
            pattern in name or name == pattern
            for pattern in upgrade_function_patterns
            for name in lowered_names
        )

    def _has_custom_return_guard(self, source_text_lower: str) -> bool:
        guard_tokens = ("transfer(", "transferfrom(", "approve(")
        for line in source_text_lower.splitlines():
            if "if" not in line:
                continue
            if not any(token in line for token in guard_tokens):
                continue
            if "!" in line or "false" in line or "==0" in line:
                return True
        return False

    def _checks_zero_address(self, require_exprs: list[str]) -> bool:
        patterns = ("address(0)", "0x0000000000000000000000000000000000000000")
        for expr in require_exprs:
            lowered = expr.lower()
            if any(pattern in lowered for pattern in patterns):
                return True
        return False

    def _checks_sig_v(self, require_exprs: list[str], parameter_names: list[str]) -> bool:
        if "v" not in {name.lower() for name in parameter_names}:
            return False
        for expr in require_exprs:
            lowered = expr.lower()
            if "v" in lowered and ("27" in lowered or "28" in lowered):
                return True
        return False

    def _checks_sig_s(self, require_exprs: list[str], parameter_names: list[str]) -> bool:
        if "s" not in {name.lower() for name in parameter_names}:
            return False
        for expr in require_exprs:
            lowered = expr.lower()
            if "s" in lowered and ("secp256" in lowered or "0x7f" in lowered or "<=" in lowered):
                return True
        return False

    def _reads_oracle_price(self, token_call_kinds: set[str]) -> bool:
        oracle_calls = {"latestanswer", "latestrounddata", "getrounddata", "getprice", "getassetprice"}
        return any(call in oracle_calls for call in token_call_kinds)

    def _oracle_call_count(self, fn: Any) -> int:
        oracle_calls = {"latestanswer", "latestrounddata", "getrounddata", "getprice", "getassetprice"}
        count = 0
        for _, call in getattr(fn, "high_level_calls", []) or []:
            name = getattr(call, "function_name", None)
            if name and str(name).lower() in oracle_calls:
                count += 1
        return count

    def _oracle_call_targets(self, high_level_calls: list[Any]) -> set[str]:
        oracle_calls = {"latestanswer", "latestrounddata", "getrounddata", "getprice", "getassetprice"}
        targets: set[str] = set()
        for _, call in high_level_calls:
            name = getattr(call, "function_name", None) or getattr(call, "name", None) or getattr(call, "full_name", None)
            if not name:
                continue
            if str(name).lower() not in oracle_calls:
                continue
            target = self._oracle_call_target_name(call)
            if target:
                targets.add(target)
        return targets

    def _oracle_call_target_name(self, call: Any) -> str | None:
        destination = getattr(call, "destination", None)
        if destination is not None:
            name = getattr(destination, "name", None)
            if name:
                return str(name)
            dest_type = getattr(destination, "type", None)
            if dest_type is not None:
                dest_name = str(dest_type)
                if dest_name and dest_name != "address":
                    return dest_name
        contract_name = self._call_contract_name(call)
        if contract_name:
            return contract_name
        return None

    def _has_staleness_check(self, require_exprs: list[str]) -> bool:
        staleness_tokens = ("updatedat", "answeredinround", "roundid")
        for expr in require_exprs:
            lowered = expr.lower()
            if any(token in lowered for token in staleness_tokens):
                return True
        return False

    def _has_staleness_threshold(self, require_exprs: list[str]) -> bool:
        tokens = ("max", "threshold", "stale", "age", "heartbeat", "delay")
        for expr in require_exprs:
            lowered = expr.lower()
            if "updatedat" not in lowered:
                continue
            if "block.timestamp" not in lowered and "-" not in lowered:
                continue
            if any(token in lowered for token in tokens) or re.search(r"\b\d+\b", lowered):
                return True
        return False

    def _has_oracle_round_check(self, require_exprs: list[str]) -> bool:
        for expr in require_exprs:
            lowered = expr.lower()
            if "answeredinround" in lowered and ("roundid" in lowered or "roundid" in lowered):
                return True
        return False

    def _has_deadline_parameter(self, parameter_names: list[str]) -> bool:
        return any(key in name.lower() for name in parameter_names for key in ("deadline", "expiry", "expiration"))

    def _has_duration_parameter(self, parameter_names: list[str]) -> bool:
        tokens = ("duration", "lock", "locking", "vesting", "period", "delay", "cooldown")
        return any(any(token in name.lower() for token in tokens) for name in parameter_names)

    def _has_duration_bounds(self, require_exprs: list[str], parameter_names: list[str]) -> bool:
        duration_names = [name for name in parameter_names if self._has_duration_parameter([name])]
        if not duration_names:
            return False
        for expr in require_exprs:
            lowered = expr.lower()
            if not any(name.lower() in lowered for name in duration_names):
                continue
            if not any(op in lowered for op in ("<=", ">=", "<", ">")):
                continue
            if any(token in lowered for token in ("min", "max", "limit")) or re.search(r"\b\d+\b", lowered):
                return True
        return False

    def _has_slippage_parameter(self, parameter_names: list[str]) -> bool:
        slippage_keys = ("minout", "amountoutmin", "minamountout", "slippage", "slippagebps")
        return any(key in name.lower() for name in parameter_names for key in slippage_keys)

    def _has_slippage_check(self, require_exprs: list[str], parameter_names: list[str]) -> bool:
        slippage_names = [name for name in parameter_names if self._has_slippage_parameter([name])]
        if not slippage_names:
            return False
        for expr in require_exprs:
            lowered = expr.lower()
            if any(name.lower() in lowered for name in slippage_names) and (">" in lowered or "<" in lowered):
                return True
        return False

    def _validates_oracle_answer_positive(self, require_exprs: list[str]) -> bool:
        for expr in require_exprs:
            lowered = expr.lower()
            if any(token in lowered for token in ("answer", "price")) and any(
                token in lowered for token in ("> 0", ">= 0", "!= 0")
            ):
                return True
        return False

    def _validates_oracle_timestamp(self, require_exprs: list[str]) -> bool:
        for expr in require_exprs:
            lowered = expr.lower()
            if "updatedat" in lowered and "block.timestamp" in lowered:
                return True
            if "timestamp" in lowered and "updatedat" in lowered:
                return True
        return False

    def _validates_oracle_started_at(self, require_exprs: list[str]) -> bool:
        for expr in require_exprs:
            lowered = expr.lower()
            if "startedat" in lowered and any(op in lowered for op in (">", "<", "!=")):
                return True
        return False

    def _has_calldata_length_check(self, require_exprs: list[str]) -> bool:
        for expr in require_exprs:
            lowered = expr.lower()
            if "length" not in lowered:
                continue
            if "calldata" in lowered or "msg.data" in lowered or "data.length" in lowered:
                return True
        return False

    def _uses_calldata_slice(self, source_text_lower: str) -> bool:
        return "msg.data[" in source_text_lower or "calldata[" in source_text_lower

    def _has_nested_loop_text(self, source_text_lower: str) -> bool:
        text = self._strip_comments(source_text_lower)
        tokens = re.finditer(r"\bfor\b|\bwhile\b|\\{|\\}", text)
        brace_depth = 0
        loop_depth = 0
        pending_loop = False
        loop_brace_depths: list[int] = []
        for match in tokens:
            token = match.group(0)
            if token in {"for", "while"}:
                pending_loop = True
                continue
            if token == "{":
                brace_depth += 1
                if pending_loop:
                    loop_depth += 1
                    if loop_depth >= 2:
                        return True
                    loop_brace_depths.append(brace_depth)
                    pending_loop = False
            elif token == "}":
                if loop_brace_depths and brace_depth == loop_brace_depths[-1]:
                    loop_depth = max(loop_depth - 1, 0)
                    loop_brace_depths.pop()
                brace_depth = max(brace_depth - 1, 0)
        return False

    def _has_bytes_length_check(self, require_exprs: list[str], bytes_param_names: list[str]) -> bool:
        if not bytes_param_names:
            return False
        for expr in require_exprs:
            lowered = expr.lower()
            if ".length" not in lowered:
                continue
            if any(name.lower() in lowered for name in bytes_param_names):
                return True
        return False

    def _uses_arithmetic(self, source_text_lower: str) -> bool:
        if re.search(r"[a-z0-9_\\)]\\s*[-+*/%]\\s*[a-z0-9_(]", source_text_lower):
            return True
        return any(
            token in source_text_lower
            for token in (" + ", " - ", " * ", " / ", "+=", "-=", "*=", "/=")
        )

    def _uses_division(self, source_text_lower: str) -> bool:
        if re.search(r"[a-z0-9_\\)]\\s*/\\s*[a-z0-9_(]", source_text_lower):
            return True
        return " / " in source_text_lower or "/ " in source_text_lower or " /" in source_text_lower

    def _divisor_sources(
        self, source_text_lower: str, parameter_names: list[str], state_var_names: list[str]
    ) -> list[str]:
        sources: set[str] = set()
        for name in parameter_names:
            lowered = name.lower()
            if f"/{lowered}" in source_text_lower or f"/ {lowered}" in source_text_lower:
                sources.add("parameter")
        for name in state_var_names:
            lowered = str(name).lower()
            if f"/{lowered}" in source_text_lower or f"/ {lowered}" in source_text_lower:
                sources.add("storage")
        if "/" in source_text_lower and not sources:
            sources.add("calculation")
        return sorted(sources)

    def _has_recursive_call(self, label: str, source_text_lower: str) -> bool:
        name = label.split("(")[0].strip().lower()
        if not name:
            return False
        token = f"{name}("
        return source_text_lower.count(token) > 1

    def _has_nonzero_check(self, require_exprs: list[str], names: list[str]) -> bool:
        if not names:
            return False
        for expr in require_exprs:
            lowered = expr.lower()
            for name in names:
                token = name.lower()
                if token not in lowered:
                    continue
                if any(op in lowered for op in ("!= 0", "> 0", ">= 1", "> 1")):
                    return True
        return False

    def _allocates_memory_array_from_input(
        self, source_text_lower: str, parameter_names: list[str]
    ) -> bool:
        if "new" not in source_text_lower or not parameter_names:
            return False
        for name in parameter_names:
            token = name.lower()
            if f"new uint256[]({token})" in source_text_lower:
                return True
            if f"new bytes({token})" in source_text_lower:
                return True
            if re.search(rf"new\\s+\\w+\\[\\]\\s*\\(\\s*{re.escape(token)}\\s*\\)", source_text_lower):
                return True
        return False

    def _handles_transfer_failure(self, require_exprs: list[str], source_text_lower: str) -> bool:
        if "try " in source_text_lower and "catch" in source_text_lower:
            return True
        for expr in require_exprs:
            lowered = expr.lower()
            if "require" not in lowered:
                continue
            if any(token in lowered for token in ("success", "ok", "send(", "call(")):
                return True
        if "if (!success" in source_text_lower or "if(!success" in source_text_lower:
            return True
        return False

    def _has_address_nonzero_check(self, require_exprs: list[str], address_param_names: list[str]) -> bool:
        if not address_param_names:
            return False
        for expr in require_exprs:
            lowered = expr.lower()
            if "address(0)" not in lowered and "0x0000000000000000000000000000000000000000" not in lowered:
                continue
            if any(name.lower() in lowered for name in address_param_names):
                return True
        return False

    def _uses_amount_division(self, amount_param_names: list[str], source_text_lower: str) -> bool:
        for name in amount_param_names:
            lowered = name.lower()
            if f"{lowered}/" in source_text_lower or f"{lowered} /" in source_text_lower:
                return True
            if f"/{lowered}" in source_text_lower or f"/ {lowered}" in source_text_lower:
                return True
            if f"div({lowered}" in source_text_lower:
                return True
        return False

    def _has_precision_guard(self, require_exprs: list[str], source_text_lower: str) -> bool:
        clean = self._strip_comments(source_text_lower)
        if "muldiv" in clean:
            return True
        tokens = ("precision", "scale")
        if any(token in clean for token in tokens):
            for line in clean.splitlines():
                if any(token in line for token in tokens) and any(op in line for op in ("*", "/")):
                    return True
        for expr in require_exprs:
            lowered = expr.lower()
            if any(token in lowered for token in tokens) and any(op in lowered for op in ("<", "<=", ">", ">=")):
                return True
        return False

    def _has_amount_bounds(self, require_exprs: list[str], amount_param_names: list[str]) -> bool:
        if not amount_param_names:
            return False
        for expr in require_exprs:
            lowered = expr.lower()
            if not any(name.lower() in lowered for name in amount_param_names):
                continue
            if not any(op in lowered for op in ("<=", ">=", "<", ">", "!=")):
                continue
            if any(token in lowered for token in ("0", "max", "min", "limit", "cap")):
                return True
        return False

    def _has_array_length_check(self, require_exprs: list[str], array_param_names: list[str]) -> bool:
        if not array_param_names:
            return False
        for expr in require_exprs:
            lowered = expr.lower()
            if ".length" not in lowered:
                continue
            if not any(name.lower() in lowered for name in array_param_names):
                continue
            if any(op in lowered for op in ("<=", ">=", "<", ">", "==", "!=")):
                return True
        return False

    def _has_array_length_match(self, require_exprs: list[str], array_param_names: list[str]) -> bool:
        if len(array_param_names) < 2:
            return False
        for expr in require_exprs:
            lowered = expr.lower()
            if ".length" not in lowered or "==" not in lowered:
                continue
            if sum(1 for name in array_param_names if name.lower() in lowered) >= 2:
                return True
        return False

    def _has_reentrancy_guard(self, modifiers: list[str], require_exprs: list[str]) -> bool:
        guard_tokens = ("nonreentrant", "reentrancyguard", "reentrancy", "mutex", "guard", "lock")
        for modifier in modifiers:
            lowered = modifier.lower()
            if any(token in lowered for token in guard_tokens):
                return True
        for expr in require_exprs:
            lowered = expr.lower()
            if not any(token in lowered for token in ("reentr", "mutex", "locked", "entered", "_status")):
                continue
            if any(op in lowered for op in ("==", "!=", "!", "not")):
                return True
        return False

    def _has_array_index_check(
        self, require_exprs: list[str], array_param_names: list[str], parameter_names: list[str]
    ) -> bool:
        if not array_param_names or not parameter_names:
            return False
        index_names = [name for name in parameter_names if any(token in name.lower() for token in ("index", "idx", "pos"))]
        if not index_names:
            return False
        for expr in require_exprs:
            lowered = expr.lower()
            if ".length" not in lowered:
                continue
            if not any(name.lower() in lowered for name in array_param_names):
                continue
            if any(name.lower() in lowered for name in index_names) and any(op in lowered for op in ("<", "<=")):
                return True
        return False

    def _has_amount_nonzero_check(self, require_exprs: list[str], amount_param_names: list[str]) -> bool:
        if not amount_param_names:
            return False
        for expr in require_exprs:
            lowered = expr.lower()
            if not any(name.lower() in lowered for name in amount_param_names):
                continue
            if "> 0" in lowered or "!= 0" in lowered or ">= 1" in lowered:
                return True
        return False

    def _has_contract_code_check(self, require_exprs: list[str]) -> bool:
        for expr in require_exprs:
            lowered = expr.lower()
            if "code.length" in lowered or "extcodesize" in lowered or "iscontract" in lowered:
                return True
        return False

    def _has_address_not_self_check(self, require_exprs: list[str], address_param_names: list[str]) -> bool:
        if not address_param_names:
            return False
        for expr in require_exprs:
            lowered = expr.lower()
            if "address(this)" not in lowered:
                continue
            if any(name.lower() in lowered for name in address_param_names):
                return True
        return False

    def _has_oracle_aggregation_sanity(self, require_exprs: list[str], source_text: str) -> bool:
        tokens = ("median", "deviation", "outlier", "threshold", "bounds")
        if any(token in source_text for token in tokens):
            return True
        for expr in require_exprs:
            lowered = expr.lower()
            if any(token in lowered for token in tokens):
                return True
        return False

    def _has_oracle_decimals_normalized(self, source_text_lower: str, require_exprs: list[str]) -> bool:
        tokens = ("decimals", "scale", "normalize", "precision")
        if any(token in source_text_lower for token in tokens):
            return True
        for expr in require_exprs:
            lowered = expr.lower()
            if any(token in lowered for token in tokens):
                return True
        return False

    def _has_oracle_min_source_count(self, require_exprs: list[str]) -> bool:
        for expr in require_exprs:
            lowered = expr.lower()
            if ".length" not in lowered:
                continue
            if any(token in lowered for token in ("sources", "oracles", "feeds")) and any(
                op in lowered for op in (">", ">=", "==")
            ):
                return True
        return False

    def _has_oracle_per_source_staleness(self, require_exprs: list[str]) -> bool:
        count = 0
        for expr in require_exprs:
            lowered = expr.lower()
            if "updatedat" in lowered or "answeredinround" in lowered:
                count += 1
        return count >= 2

    def _has_oracle_time_alignment(self, require_exprs: list[str]) -> bool:
        for expr in require_exprs:
            lowered = expr.lower()
            if "updatedat" not in lowered:
                continue
            if "-" in lowered and any(op in lowered for op in ("<", "<=", ">", ">=")):
                return True
        return False

    def _has_oracle_weighted_aggregation(self, source_text_lower: str, require_exprs: list[str]) -> bool:
        tokens = ("weight", "weighted", "weights")
        if any(token in source_text_lower for token in tokens):
            return True
        for expr in require_exprs:
            lowered = expr.lower()
            if any(token in lowered for token in tokens):
                return True
        return False

    def _has_oracle_circuit_breaker(self, source_text_lower: str, require_exprs: list[str]) -> bool:
        tokens = ("circuit", "breaker", "pause", "halt", "emergency")
        if any(token in source_text_lower for token in tokens):
            return True
        for expr in require_exprs:
            lowered = expr.lower()
            if any(token in lowered for token in tokens):
                return True
        return False

    def _has_oracle_disagreement_fallback(self, source_text_lower: str, require_exprs: list[str]) -> bool:
        tokens = ("fallback", "backup", "secondary", "disagree")
        if any(token in source_text_lower for token in tokens):
            return True
        for expr in require_exprs:
            lowered = expr.lower()
            if any(token in lowered for token in tokens):
                return True
        return False

    def _has_oracle_min_agreement(self, source_text_lower: str, require_exprs: list[str]) -> bool:
        tokens = ("agreement", "quorum", "minagree", "consensus")
        if any(token in source_text_lower for token in tokens):
            return True
        for expr in require_exprs:
            lowered = expr.lower()
            if any(token in lowered for token in tokens):
                return True
        return False

    def _has_oracle_source_health_check(self, source_text_lower: str, require_exprs: list[str]) -> bool:
        tokens = ("health", "status", "valid", "up")
        if any(token in source_text_lower for token in tokens):
            return True
        for expr in require_exprs:
            lowered = expr.lower()
            if any(token in lowered for token in tokens):
                return True
        return False

    def _has_oracle_update_frequency_alignment(self, source_text_lower: str, require_exprs: list[str]) -> bool:
        tokens = ("frequency", "interval", "heartbeat", "cadence")
        if any(token in source_text_lower for token in tokens):
            return True
        for expr in require_exprs:
            lowered = expr.lower()
            if any(token in lowered for token in tokens):
                return True
        return False

    def _is_oracle_update_function(self, label: str) -> bool:
        lowered = label.lower()
        tokens = ("setoracle", "setprice", "setfeed", "setaggregator", "updateoracle", "updateprice")
        return any(token in lowered for token in tokens)

    def _has_oracle_update_rate_limit(self, require_exprs: list[str], source_text_lower: str) -> bool:
        tokens = ("lastupdate", "cooldown", "rate", "interval", "minupdate", "nextupdate", "minupdatedelay")
        for expr in require_exprs:
            lowered = expr.lower()
            if "block.timestamp" in lowered and any(token in lowered for token in tokens):
                return True
        return False

    def _has_oracle_update_timelock(self, require_exprs: list[str], source_text_lower: str) -> bool:
        tokens = ("timelock", "eta", "unlock", "delay")
        if any(token in source_text_lower for token in tokens):
            return True
        for expr in require_exprs:
            lowered = expr.lower()
            if any(token in lowered for token in tokens) and any(op in lowered for op in (">", "<", ">=", "<=")):
                return True
        return False

    def _has_oracle_update_deviation_check(self, require_exprs: list[str], source_text_lower: str) -> bool:
        tokens = ("deviation", "maxchange", "delta", "bounds", "threshold", "percent")
        if any(token in source_text_lower for token in tokens):
            return True
        for expr in require_exprs:
            lowered = expr.lower()
            if any(token in lowered for token in tokens) and any(op in lowered for op in (">", "<", ">=", "<=")):
                return True
        return False

    def _has_oracle_update_signature_check(self, source_text_lower: str) -> bool:
        tokens = ("signature", "sig", "ecrecover", "recover")
        return any(token in source_text_lower for token in tokens)

    def _has_oracle_update_sequence_check(self, require_exprs: list[str], source_text_lower: str) -> bool:
        tokens = ("nonce", "sequence", "seq", "round", "order")
        if any(token in source_text_lower for token in tokens):
            return True
        for expr in require_exprs:
            lowered = expr.lower()
            if any(token in lowered for token in tokens):
                return True
        return False

    def _has_oracle_update_timestamp_check(self, require_exprs: list[str]) -> bool:
        for expr in require_exprs:
            lowered = expr.lower()
            if "timestamp" in lowered and any(op in lowered for op in (">", "<", ">=", "<=")):
                return True
        return False

    def _has_cross_chain_context(self, reads_state: list[Any], contract: Any, source_text: str) -> bool:
        tokens = ("bridge", "cross", "l1", "l2", "layerzero", "wormhole")
        if any(token in source_text for token in tokens):
            return True
        for var in reads_state:
            name = getattr(var, "name", None)
            if name and any(token in name.lower() for token in tokens):
                return True
        for var in getattr(contract, "state_variables", []) or []:
            name = getattr(var, "name", None)
            if name and any(token in name.lower() for token in tokens):
                return True
        return False

    def _has_cross_chain_validation(self, require_exprs: list[str], source_text: str) -> bool:
        tokens = ("proof", "merkle", "nonce", "message", "verify", "signature")
        if any(token in source_text for token in tokens):
            return True
        for expr in require_exprs:
            lowered = expr.lower()
            if any(token in lowered for token in tokens):
                return True
        return False

    def _has_cross_chain_consistency_check(self, require_exprs: list[str], source_text_lower: str) -> bool:
        tokens = ("l1", "l2", "mainnet", "rollup")
        compare_tokens = ("diff", "delta", "compare", "consistent", "match")
        if any(token in source_text_lower for token in tokens) and any(
            token in source_text_lower for token in compare_tokens
        ):
            return True
        for expr in require_exprs:
            lowered = expr.lower()
            if any(token in lowered for token in tokens) and any(token in lowered for token in compare_tokens):
                return True
        return False

    def _has_bridge_finality_check(self, require_exprs: list[str], source_text_lower: str) -> bool:
        tokens = ("confirm", "finality", "finalized", "depth", "confirmations")
        if any(token in source_text_lower for token in tokens):
            return True
        for expr in require_exprs:
            lowered = expr.lower()
            if any(token in lowered for token in tokens):
                return True
        return False

    def _has_bridge_source_chain_check(self, source_text_lower: str, require_exprs: list[str]) -> bool:
        tokens = ("sourcechain", "srcchain", "origin", "source")
        if any(token in source_text_lower for token in tokens):
            return True
        for expr in require_exprs:
            lowered = expr.lower()
            if any(token in lowered for token in tokens):
                return True
        return False

    def _has_bridge_ordering_check(self, source_text_lower: str, require_exprs: list[str]) -> bool:
        tokens = ("order", "sequence", "nonce", "seq")
        if any(token in source_text_lower for token in tokens):
            return True
        for expr in require_exprs:
            lowered = expr.lower()
            if any(token in lowered for token in tokens):
                return True
        return False

    def _has_bridge_replay_protection(self, require_exprs: list[str], source_text_lower: str) -> bool:
        tokens = ("nonce", "sequence", "replay", "consumed", "used")
        if any(token in source_text_lower for token in tokens):
            return True
        for expr in require_exprs:
            lowered = expr.lower()
            if any(token in lowered for token in tokens):
                return True
        return False

    def _uses_fixed_oracle_decimals(self, source_text: str) -> bool:
        tokens = ("1e8", "10**8", "10** 8", "1e18")
        return any(token in source_text for token in tokens)

    def _reads_twap(self, token_call_kinds: set[str], source_text_lower: str) -> bool:
        twap_calls = {"consult", "observe", "twap", "gettwap", "price0cumulative", "price1cumulative"}
        if any(call in twap_calls for call in token_call_kinds):
            return True
        return any(token in source_text_lower for token in ("consult(", "observe(", "twap", "price0cumulative"))

    def _price_input_used_in_calc(self, source_text_lower: str) -> tuple[bool, set[str]]:
        call_tokens = (
            "latestanswer",
            "latestrounddata",
            "getrounddata",
            "getprice",
            "getassetprice",
            "getreserves",
        )
        if not any(token in source_text_lower for token in call_tokens):
            return False, set()
        call_pattern = "|".join(call_tokens)
        if re.search(rf"({call_pattern})\s*\([^;]*\)\s*(?:\*|\+|/|-)", source_text_lower):
            return True, set()
        if re.search(rf"(?:\*|\+|/|-)\s*({call_pattern})\s*\(", source_text_lower):
            return True, set()
        assigned = self._extract_call_assignment_names(source_text_lower, call_tokens)
        derived = self._extract_derived_price_vars(source_text_lower, assigned)
        price_vars = assigned | derived
        for name in assigned:
            if re.search(rf"\b{name}\b[^;\n]*?(?:\*|\+|/|-)", source_text_lower):
                return True, price_vars
            if re.search(rf"(?:\*|\+|/|-)[^;\n]*?\b{name}\b", source_text_lower):
                return True, price_vars
        return False, price_vars

    def _extract_derived_price_vars(self, source_text_lower: str, source_vars: set[str]) -> set[str]:
        if not source_vars:
            return set()
        derived: set[str] = set()
        for line in source_text_lower.splitlines():
            if line.lstrip().startswith("("):
                continue
            if not any(var in line for var in source_vars):
                continue
            match = re.search(r"(?:\w+\s+)?([a-zA-Z_][a-zA-Z0-9_]*)\s*=", line)
            if match:
                derived.add(match.group(1))
        return derived

    def _price_input_used_in_value_sink(
        self,
        source_text_lower: str,
        price_vars: set[str],
        state_var_names: list[str],
    ) -> bool:
        if not source_text_lower:
            return False
        value_tokens = (
            "transfer(",
            "transferfrom(",
            "safetransfer(",
            "safetransferfrom(",
            "safebatchtransferfrom(",
            "send(",
            "call{value",
        )
        call_tokens = (
            "latestanswer",
            "latestrounddata",
            "getrounddata",
            "getprice",
            "getassetprice",
            "getreserves",
        )
        state_tokens = [name.lower() for name in state_var_names if name]
        assignment_ops = ("+=", "-=", "=")
        for line in source_text_lower.splitlines():
            has_price_var = any(var in line for var in price_vars) if price_vars else False
            has_call_token = any(token in line for token in call_tokens)
            if not has_price_var and not has_call_token:
                continue
            if any(token in line for token in value_tokens):
                return True
            if any(op in line for op in assignment_ops):
                for token in state_tokens:
                    if f"{token}[" in line and any(op in line for op in assignment_ops):
                        return True
                    if f"{token} +=" in line or f"{token}+=" in line:
                        return True
                    if f"{token} -=" in line or f"{token}-=" in line:
                        return True
                    if f"{token} =" in line or f"{token}=" in line:
                        return True
        return False

    def _extract_call_assignment_names(self, source_text_lower: str, call_tokens: tuple[str, ...]) -> set[str]:
        assignments: set[str] = set()
        call_pattern = "|".join(re.escape(token) for token in call_tokens)
        try:
            tuple_matches = re.finditer(
                rf"\(([^)]*)\)\s*=\s*[^;]*({call_pattern})", source_text_lower
            )
        except re.error:
            return set()
        for match in tuple_matches:
            params = match.group(1)
            for part in params.split(","):
                token = part.strip()
                if not token or token == "_":
                    continue
                name_match = re.search(r"([a-zA-Z_][a-zA-Z0-9_]*)$", token)
                if name_match:
                    assignments.add(name_match.group(1))
        try:
            scalar_matches = re.finditer(
                rf"([a-zA-Z_][a-zA-Z0-9_]*)\s*=\s*[^;]*({call_pattern})", source_text_lower
            )
        except re.error:
            return assignments
        for match in scalar_matches:
            assignments.add(match.group(1))
        return assignments

    def _has_twap_window_parameter(self, parameter_names: list[str]) -> bool:
        window_keys = ("secondsago", "window", "interval", "twapwindow", "period")
        return any(key in name.lower() for name in parameter_names for key in window_keys)

    def _has_twap_observation_check(self, require_exprs: list[str], source_text_lower: str) -> bool:
        tokens = ("observation", "cardinality", "observations")
        if any(token in source_text_lower for token in tokens):
            return True
        for expr in require_exprs:
            lowered = expr.lower()
            if any(token in lowered for token in tokens):
                return True
        return False

    def _has_twap_window_min_check(self, require_exprs: list[str], parameter_names: list[str]) -> bool:
        window_names = [name for name in parameter_names if self._has_twap_window_parameter([name])]
        if not window_names:
            return False
        for expr in require_exprs:
            lowered = expr.lower()
            if not any(name.lower() in lowered for name in window_names):
                continue
            if any(op in lowered for op in (">=", ">")) and (
                "min" in lowered or "minwindow" in lowered or re.search(r"\b\d+\b", lowered)
            ):
                return True
        return False

    def _has_twap_timestamp_check(self, require_exprs: list[str]) -> bool:
        for expr in require_exprs:
            lowered = expr.lower()
            if "timestamp" in lowered and any(token in lowered for token in ("twap", "secondsago", "window", "interval")):
                return True
        return False

    def _has_twap_price_bounds(self, require_exprs: list[str]) -> bool:
        for expr in require_exprs:
            lowered = expr.lower()
            if "price" in lowered or "twap" in lowered:
                if any(op in lowered for op in ("<", ">", "<=", ">=")):
                    return True
        return False

    def _has_twap_gap_handling(self, source_text_lower: str, require_exprs: list[str]) -> bool:
        tokens = ("gap", "interpolat", "fill")
        if any(token in source_text_lower for token in tokens):
            return True
        for expr in require_exprs:
            lowered = expr.lower()
            if any(token in lowered for token in tokens):
                return True
        return False

    def _has_twap_volatility_window(self, source_text_lower: str, require_exprs: list[str]) -> bool:
        tokens = ("volatility", "vol", "variance")
        if any(token in source_text_lower for token in tokens):
            return True
        for expr in require_exprs:
            lowered = expr.lower()
            if any(token in lowered for token in tokens):
                return True
        return False

    def _has_sequencer_uptime_check(self, require_exprs: list[str]) -> bool:
        tokens = ("sequencer", "uptime", "grace", "l2")
        return any(any(token in expr.lower() for token in tokens) for expr in require_exprs)

    def _has_sequencer_grace_period(self, require_exprs: list[str]) -> bool:
        for expr in require_exprs:
            lowered = expr.lower()
            if "sequencer" not in lowered:
                continue
            if "grace" in lowered or "graceperiod" in lowered:
                return True
        return False

    def _has_l2_finality_check(self, require_exprs: list[str], source_text_lower: str) -> bool:
        tokens = ("finality", "confirmations", "challenge", "reorg", "fraud", "rollback")
        for expr in require_exprs:
            lowered = expr.lower()
            if any(token in lowered for token in tokens) and any(op in lowered for op in (">", "<", ">=", "<=")):
                return True
        return False

    def _l2_oracle_context(
        self, reads_state: list[Any], contract: Any, require_exprs: list[str], source_text_lower: str
    ) -> bool:
        if any("sequencer" in expr.lower() for expr in require_exprs):
            return True
        if any(token in source_text_lower for token in ("sequencer", "l2", "rollup", "optimism", "arbitrum")):
            return True
        for var in reads_state:
            name = getattr(var, "name", None)
            if name and ("sequencer" in name.lower() or "l2" in name.lower()):
                return True
        for var in getattr(contract, "state_variables", []) or []:
            name = getattr(var, "name", None)
            if name and ("sequencer" in name.lower() or "l2" in name.lower()):
                return True
        return False

    def _has_v3_struct_params(self, fn: Any) -> bool:
        for param in getattr(fn, "parameters", []) or []:
            name = getattr(param, "name", "") or ""
            if name.lower() == "params":
                return True
            param_type = getattr(param, "type", None)
            if param_type is None:
                continue
            type_name = str(param_type)
            if "ExactInputSingleParams" in type_name or "ExactOutputSingleParams" in type_name:
                return True
            if "tuple" in type_name.lower():
                return True
        return False

    def _is_swap_like(self, fn_name: str, token_call_kinds: set[str], parameter_names: list[str]) -> bool:
        lowered = fn_name.lower()
        swap_tokens = ("swap", "exactinput", "exactoutput", "sell", "buy")
        if any(token in lowered for token in swap_tokens):
            return True
        if any(self._is_swap_call_kind(kind) for kind in token_call_kinds):
            return True
        if any("amountoutmin" in name.lower() for name in parameter_names):
            return True
        return False

    def _is_swap_call_kind(self, kind: str) -> bool:
        lowered = kind.lower()
        swap_kinds = (
            "swap",
            "swapexacttokensfortokens",
            "swapexactethfortokens",
            "swapexacttokensforeth",
            "swaptokensforexacttokens",
            "swapexactinput",
            "swapexactoutput",
            "exactinput",
            "exactoutput",
            "exactinputsingle",
            "exactoutputsingle",
            "multicall",
        )
        return any(token in lowered for token in swap_kinds)

    def _fn_name_has_voting_tokens(self, label: str) -> bool:
        lowered = label.lower()
        return any(token in lowered for token in ("vote", "voting", "govern", "quorum", "proposal"))

    def _is_multisig_threshold_change(self, label: str, parameter_names: list[str]) -> bool:
        lowered = label.lower()
        if "threshold" in lowered:
            return True
        return any("threshold" in name.lower() for name in parameter_names)

    def _is_multisig_member_change(self, label: str, parameter_names: list[str]) -> bool:
        lowered = label.lower()
        tokens = ("signer", "signers", "owner", "owners", "member", "members")
        if any(token in lowered for token in tokens):
            return True
        return any(any(token in name.lower() for token in tokens) for name in parameter_names)

    def _is_role_grant_like(self, label: str, parameter_names: list[str]) -> bool:
        lowered = label.lower()
        tokens = ("grant", "addrole", "setrole", "assignrole")
        if any(token in lowered for token in tokens):
            return True
        return any(any(token in name.lower() for token in tokens) for name in parameter_names)

    def _is_role_revoke_like(self, label: str, parameter_names: list[str]) -> bool:
        lowered = label.lower()
        tokens = ("revoke", "removerole", "revokerole")
        if any(token in lowered for token in tokens):
            return True
        return any(any(token in name.lower() for token in tokens) for name in parameter_names)

    def _has_named_bounds(
        self, require_exprs: list[str], parameter_names: list[str], tokens: set[str]
    ) -> bool:
        if not parameter_names:
            return False
        candidate_params = [
            name for name in parameter_names if any(token in name.lower() for token in tokens)
        ]
        if not candidate_params:
            return False
        for expr in require_exprs:
            lowered = expr.lower()
            if not any(name.lower() in lowered for name in candidate_params):
                continue
            if any(op in lowered for op in ("<=", "<", ">=", ">", "==")):
                return True
        return False

    def _has_parameter_bounds(self, require_exprs: list[str], parameter_names: list[str]) -> bool:
        if not parameter_names:
            return False
        for expr in require_exprs:
            lowered = expr.lower()
            if not any(name.lower() in lowered for name in parameter_names):
                continue
            if any(op in lowered for op in ("<=", "<", ">=", ">", "==")):
                return True
        return False

    def _is_governance_execute_function(self, label: str) -> bool:
        lowered = label.lower()
        tokens = ("execute", "finalize", "queue", "enact", "cancel")
        return any(token in lowered for token in tokens)

    def _has_quorum_check(self, require_exprs: list[str]) -> bool:
        for expr in require_exprs:
            lowered = expr.lower()
            if "quorum" in lowered:
                return True
        return False

    def _has_voting_period_check(self, require_exprs: list[str]) -> bool:
        tokens = ("deadline", "end", "vote", "voting", "period", "window")
        for expr in require_exprs:
            lowered = expr.lower()
            if any(token in lowered for token in tokens) and any(
                time_token in lowered for time_token in ("block.timestamp", "block.number")
            ):
                return True
        return False

    def _access_gate_uses_balance_check(self, require_exprs: list[str]) -> bool:
        tokens = ("balance", "balanceof")
        for expr in require_exprs:
            lowered = expr.lower()
            if any(token in lowered for token in tokens) and "require" in lowered:
                return True
        return False

    def _access_gate_uses_contract_address(self, require_exprs: list[str]) -> bool:
        for expr in require_exprs:
            lowered = expr.lower()
            if "address(this)" in lowered and "msg.sender" in lowered:
                return True
        return False

    def _access_gate_uses_hash_compare(self, require_exprs: list[str]) -> bool:
        for expr in require_exprs:
            lowered = expr.lower()
            if "keccak256" in lowered and ("==" in lowered or "!=" in lowered):
                return True
        return False

    def _access_gate_has_if_return(self, source_text_lower: str) -> bool:
        if "if" not in source_text_lower:
            return False
        if "msg.sender" not in source_text_lower and "tx.origin" not in source_text_lower:
            return False
        return "return" in source_text_lower and "revert" not in source_text_lower

    def _has_non_sender_access_gate(self, require_exprs: list[str], parameter_names: list[str]) -> bool:
        identity_tokens = (
            "owner",
            "admin",
            "guardian",
            "role",
            "whitelist",
            "blacklist",
            "allowlist",
            "denylist",
            "operator",
            "pauser",
            "minter",
            "governor",
            "authority",
        )
        time_tokens = (
            "block.timestamp",
            "block.number",
            "blockhash",
            "block.prevrandao",
            "block.chainid",
            "msg.value",
        )
        parameter_tokens = [name.lower() for name in parameter_names if name]
        for expr in require_exprs:
            lowered = expr.lower()
            if "msg.sender" in lowered or "tx.origin" in lowered:
                continue
            if any(token in lowered for token in time_tokens):
                return True
            if any(token in lowered for token in identity_tokens):
                return True
            if any(name in lowered for name in ("caller", "sender", "origin") if name in parameter_tokens):
                return True
        return False

    def _has_min_signer_check(self, require_exprs: list[str]) -> bool:
        tokens = ("owners.length", "signers.length", "members.length", "owner_count", "signer_count")
        for expr in require_exprs:
            lowered = expr.lower()
            if any(token in lowered for token in tokens) and any(op in lowered for op in (">", ">=")):
                return True
        return False

    def _has_threshold_vs_owner_check(self, require_exprs: list[str]) -> bool:
        tokens = ("threshold", "owners.length", "signers.length", "members.length", "owner_count", "signer_count")
        for expr in require_exprs:
            lowered = expr.lower()
            if "threshold" not in lowered:
                continue
            if any(token in lowered for token in tokens) and any(op in lowered for op in ("<=", "<", ">=", ">")):
                return True
        return False

    def _balance_used_for_collateralization(
        self,
        label: str,
        parameter_names: list[str],
        reads_balance_or_reserves: bool,
        reads_oracle_price: bool,
        reads_dex_reserves: bool,
        reads_twap: bool,
    ) -> bool:
        tokens = ("collateral", "borrow", "lend", "loan", "liquidat", "margin", "leverage")
        lowered_label = label.lower()
        if any(token in lowered_label for token in tokens):
            return True
        if any(any(token in name.lower() for token in tokens) for name in parameter_names):
            return True
        if reads_balance_or_reserves:
            return True
        return bool(reads_oracle_price or reads_dex_reserves or reads_twap)

    def _uses_snapshot(self, label: str, parameter_names: list[str], require_exprs: list[str]) -> bool:
        tokens = ("snapshot", "checkpoint")
        if any(token in label.lower() for token in tokens):
            return True
        if any(any(token in name.lower() for token in tokens) for name in parameter_names):
            return True
        for expr in require_exprs:
            lowered = expr.lower()
            if any(token in lowered for token in tokens):
                return True
        return False

    def _has_merkle_leaf_domain_separator(self, source_text: str) -> bool:
        if "merkle" not in source_text or "leaf" not in source_text:
            return False
        if "0x00" in source_text or "0x01" in source_text:
            return True
        if "bytes1(0x00)" in source_text or "bytes1(0x01)" in source_text:
            return True
        return False

    def _has_require_bounds(self, require_exprs: list[str], parameter_names: list[str]) -> bool:
        """Detect if require() statements bound loop parameters (e.g., require(end - start <= MAX))."""
        if not parameter_names:
            return False
        for expr in require_exprs:
            lowered = expr.lower()
            # Check for parameter bounds: require(param <= MAX), require(end - start <= MAX)
            has_param = any(name.lower() in lowered for name in parameter_names)
            has_bound_op = any(op in lowered for op in ("<=", "<", ">=", ">"))
            # Look for MAX, max, limit keywords or numeric constants
            has_max = any(keyword in lowered for keyword in ("max", "limit", "bound"))
            has_constant = re.search(r"\b\d+\b", lowered) is not None
            if has_param and has_bound_op and (has_max or has_constant):
                return True
        return False

    def _has_balance_check(self, require_exprs: list[str]) -> bool:
        for expr in require_exprs:
            lowered = expr.lower()
            if "balance" in lowered or "balances" in lowered or "balanceof" in lowered:
                return True
        return False

    def _checks_received_amount(self, require_exprs: list[str]) -> bool:
        for expr in require_exprs:
            lowered = expr.lower()
            if "received" in lowered or "balanceof" in lowered:
                return True
        return False

    def _has_pause_check(self, require_exprs: list[str]) -> bool:
        for expr in require_exprs:
            lowered = expr.lower()
            if "pause" in lowered or "paused" in lowered:
                return True
        return False

    def _uses_allowance_adjust(self, token_call_kinds: set[str]) -> bool:
        return any(
            kind in token_call_kinds
            for kind in ("increaseallowance", "decreaseallowance", "safeincreaseallowance", "safedecreaseallowance")
        )

    def _is_withdraw_like(self, name: str) -> bool:
        lowered = name.lower()
        return any(token in lowered for token in ("withdraw", "redeem", "claim", "unstake", "exit", "release"))

    def _is_deposit_like(self, name: str) -> bool:
        lowered = name.lower()
        return any(token in lowered for token in ("deposit", "mint", "stake", "addliquidity", "enter"))

    def _is_mint_like(self, name: str) -> bool:
        lowered = name.lower()
        return "mint" in lowered

    def _is_burn_like(self, name: str) -> bool:
        lowered = name.lower()
        return "burn" in lowered

    def _is_reward_like(self, name: str) -> bool:
        lowered = name.lower()
        tokens = ("reward", "rewards", "distribute", "harvest", "claim", "incentive", "emission", "payout")
        return any(token in lowered for token in tokens)

    def _is_liquidation_like(self, name: str) -> bool:
        lowered = name.lower()
        return "liquidat" in lowered

    def _is_flash_loan_callback(self, name: str) -> bool:
        lowered = name.lower()
        return any(
            token in lowered
            for token in (
                "executeoperation",
                "onflashloan",
                "receiveflashloan",
                "flashloan",
                "flashloancallback",
            )
        )

    def _has_flash_loan_validation(self, require_exprs: list[str]) -> bool:
        for expr in require_exprs:
            lowered = expr.lower()
            if any(token in lowered for token in ("initiator", "fee", "repay", "loan", "flash")):
                return True
        return False

    def _has_flash_loan_initiator_check(self, require_exprs: list[str]) -> bool:
        for expr in require_exprs:
            lowered = expr.lower()
            if any(token in lowered for token in ("initiator", "caller")):
                return True
            if "msg.sender" in lowered and any(token in lowered for token in ("pool", "lender", "flash")):
                return True
        return False

    def _has_flash_loan_repayment_check(self, require_exprs: list[str]) -> bool:
        for expr in require_exprs:
            lowered = expr.lower()
            if any(token in lowered for token in ("repay", "repayment", "premium", "fee", "amount +", "amount+")):
                return True
            if "balance" in lowered and "amount" in lowered and any(
                token in lowered for token in ("premium", "fee", "repay")
            ):
                return True
        return False

    def _has_flash_loan_asset_check(self, require_exprs: list[str]) -> bool:
        for expr in require_exprs:
            lowered = expr.lower()
            if "asset" in lowered and any(token in lowered for token in ("==", "!=", "address(0)")):
                return True
            if "token" in lowered and any(token in lowered for token in ("==", "!=", "address(0)")):
                return True
        return False

    def _has_flash_loan_initiator_check(self, require_exprs: list[str]) -> bool:
        for expr in require_exprs:
            lowered = expr.lower()
            if "initiator" in lowered and any(op in lowered for op in ("==", "!=")):
                return True
        return False

    def _has_flash_loan_repayment_check(self, require_exprs: list[str]) -> bool:
        for expr in require_exprs:
            lowered = expr.lower()
            if "repay" in lowered or "repayment" in lowered:
                return True
            if "amount" in lowered and "flash" in lowered:
                return True
        return False

    def _has_flash_loan_guard(self, modifiers: list[str]) -> bool:
        for modifier in modifiers:
            lowered = modifier.lower()
            if "flash" in lowered:
                return True
        return False

    def _uses_transfer(self, fn: Any) -> bool:
        """Detect usage of .transfer() method (fixed gas stipend)."""
        for node in getattr(fn, "nodes", []) or []:
            expression = self._node_expression(node)
            if ".transfer(" in expression:
                return True
            # Check IR for transfer calls
            for ir in getattr(node, "irs", []) or []:
                ir_str = str(ir).lower()
                if "transfer(" in ir_str:
                    return True
        return False

    def _uses_send(self, fn: Any) -> bool:
        """Detect usage of .send() method (fixed gas stipend)."""
        for node in getattr(fn, "nodes", []) or []:
            expression = self._node_expression(node)
            if ".send(" in expression:
                return True
            # Check IR for send calls
            for ir in getattr(node, "irs", []) or []:
                ir_str = str(ir).lower()
                if "send(" in ir_str:
                    return True
        return False

    def _has_strict_equality_check(self, require_exprs: list[str], source_text: str = "") -> bool:
        """Detect strict equality checks on balance/supply that can be manipulated for DoS.

        Detects patterns like:
        - require(address(this).balance == X)
        - if (shares != assets) revert
        - if (convertToShares(totalSupply) != balanceBefore) revert
        - assert(balance == expected)

        These are dangerous because attackers can send tokens/ETH directly to break invariants.
        """
        # Check require/assert expressions
        for expr in require_exprs:
            lowered = expr.lower()
            # Balance/supply related keywords that can be manipulated
            balance_keywords = ["balance", "totalsupply", "totalassets", "shares", "supply"]
            has_balance = any(kw in lowered for kw in balance_keywords)
            # Strict equality (== or !=)
            has_strict_eq = "==" in expr or "!=" in expr
            if has_balance and has_strict_eq:
                return True

        # Check source text for if-revert patterns (common in modern Solidity with custom errors)
        if source_text:
            source_lower = source_text.lower()
            import re
            # Check each line for if-revert with strict equality on balance-like values
            for line in source_lower.splitlines():
                # Skip if no if statement
                if 'if' not in line or ('==' not in line and '!=' not in line):
                    continue
                # Check for if statement with revert
                if re.search(r'if\s*\(', line) and 'revert' in line:
                    # Check for balance/supply related keywords
                    balance_keywords = ['balance', 'totalsupply', 'totalassets', 'shares', 'supply',
                                       'converttoshares', 'converttoassets']
                    if any(kw in line for kw in balance_keywords):
                        return True

        return False

    def _normalize_state_mutability(self, fn: Any) -> str:
        """Normalize state mutability to: view, pure, payable, or nonpayable."""
        # Check Slither's properties
        if getattr(fn, "pure", None):
            return "pure"
        if getattr(fn, "view", None):
            return "view"
        if getattr(fn, "payable", None):
            return "payable"
        # Get state_mutability attribute
        state_mut = getattr(fn, "state_mutability", None)
        if state_mut:
            state_mut_str = str(state_mut).lower()
            if "pure" in state_mut_str:
                return "pure"
            if "view" in state_mut_str:
                return "view"
            if "payable" in state_mut_str:
                return "payable"
        # Default to nonpayable
        return "nonpayable"

    def _augment_taint(
        self,
        graph: KnowledgeGraph,
        fn: Any,
        contract: Any,
        fn_node: Node,
        input_sources: list[Any],
        special_sources: list[Any],
    ) -> None:
        file_path = fn_node.properties.get("file")
        line_start = fn_node.properties.get("line_start")
        line_end = fn_node.properties.get("line_end")
        for source in input_sources + special_sources:
            node_id = self._node_id("input", f"{fn_node.id}:{source.name}", file_path, line_start)
            graph.add_node(
                Node(
                    id=node_id,
                    type="Input",
                    label=source.name,
                    properties={
                        "kind": source.kind,
                        "file": file_path,
                        "line_start": line_start,
                        "line_end": line_end,
                    },
                    evidence=self._evidence(file_path, line_start, line_end),
                )
            )
            graph.add_edge(
                Edge(
                    id=self._edge_id("FUNCTION_HAS_INPUT", fn_node.id, node_id),
                    type="FUNCTION_HAS_INPUT",
                    source=fn_node.id,
                    target=node_id,
                )
            )

        dataflow_edges, dataflow_available = compute_dataflow(
            contract,
            input_sources,
            getattr(fn, "state_variables_written", []) or [],
        )
        if dataflow_edges:
            for source, state_var in dataflow_edges:
                file_path_var, line_start_var, line_end_var = self._source_location(state_var)
                state_node_id = self._node_id(
                    "state",
                    f"{contract.name}.{state_var.name}",
                    file_path_var,
                    line_start_var,
                )
                graph.add_node(
                    Node(
                        id=state_node_id,
                        type="StateVariable",
                        label=state_var.name,
                        properties={
                            "file": file_path_var,
                            "line_start": line_start_var,
                            "line_end": line_end_var,
                        },
                        evidence=self._evidence(file_path_var, line_start_var, line_end_var),
                    )
                )
                input_node_id = self._node_id(
                    "input",
                    f"{fn_node.id}:{source.name}",
                    file_path,
                    line_start,
                )
                graph.add_edge(
                    Edge(
                        id=self._edge_id("INPUT_TAINTS_STATE", input_node_id, state_node_id),
                        type="INPUT_TAINTS_STATE",
                        source=input_node_id,
                        target=state_node_id,
                    )
                )
                graph.add_edge(
                    Edge(
                        id=self._edge_id("FUNCTION_INPUT_TAINTS_STATE", fn_node.id, state_node_id),
                        type="FUNCTION_INPUT_TAINTS_STATE",
                        source=fn_node.id,
                        target=state_node_id,
                    )
                )

        is_public = fn_node.properties.get("visibility") in {"public", "external"}
        exclude = {"msg.sender"}
        attacker_sources = [s for s in input_sources if s.name not in exclude]
        attacker_controlled_write = bool(dataflow_edges) and bool(attacker_sources) and is_public
        heuristic_write = False
        if not dataflow_available:
            heuristic_write = bool(attacker_sources) and bool(fn_node.properties.get("writes_state")) and is_public

        fn_node.properties["taint_dataflow_available"] = dataflow_available
        fn_node.properties["attacker_controlled_write"] = attacker_controlled_write
        fn_node.properties["attacker_controlled_write_heuristic"] = heuristic_write

    def _link_modifiers(self, graph: KnowledgeGraph, fn: Any, fn_node: Node) -> None:
        for modifier in getattr(fn, "modifiers", []):
            file_path, line_start, line_end = self._source_location(modifier)
            node_id = self._node_id("modifier", modifier.name, file_path, line_start)
            graph.add_node(
                Node(
                    id=node_id,
                    type="Modifier",
                    label=modifier.name,
                    properties={
                        "file": file_path,
                        "line_start": line_start,
                        "line_end": line_end,
                    },
                    evidence=self._evidence(file_path, line_start, line_end),
                )
            )
            graph.add_edge(
                Edge(
                    id=self._edge_id("USES_MODIFIER", fn_node.id, node_id),
                    type="USES_MODIFIER",
                    source=fn_node.id,
                    target=node_id,
                )
            )

    def _link_state_vars(self, graph: KnowledgeGraph, fn: Any, fn_node: Node, contract: Any) -> None:
        for var in getattr(fn, "state_variables_read", []):
            self._link_state_var(graph, fn_node, contract, var, "READS_STATE")
        for var in getattr(fn, "state_variables_written", []):
            self._link_state_var(graph, fn_node, contract, var, "WRITES_STATE")

    def _link_state_var(self, graph: KnowledgeGraph, fn_node: Node, contract: Any, var: Any, edge_type: str) -> None:
        file_path, line_start, line_end = self._source_location(var)
        node_id = self._node_id("state", f"{contract.name}.{var.name}", file_path, line_start)
        graph.add_node(
            Node(
                id=node_id,
                type="StateVariable",
                label=var.name,
                properties={
                    "file": file_path,
                    "line_start": line_start,
                    "line_end": line_end,
                },
                evidence=self._evidence(file_path, line_start, line_end),
            )
        )
        graph.add_edge(
            Edge(
                id=self._edge_id(edge_type, fn_node.id, node_id),
                type=edge_type,
                source=fn_node.id,
                target=node_id,
            )
        )

    def _link_calls(self, graph: KnowledgeGraph, fn: Any, fn_node: Node) -> None:
        for call in getattr(fn, "internal_calls", []):
            target_id = self._ensure_call_target(graph, call)
            graph.add_edge(
                Edge(
                    id=self._edge_id("CALLS_INTERNAL", fn_node.id, target_id),
                    type="CALLS_INTERNAL",
                    source=fn_node.id,
                    target=target_id,
                )
            )
        for call in getattr(fn, "external_calls", []):
            target_id = self._ensure_call_target(graph, call)
            graph.add_edge(
                Edge(
                    id=self._edge_id("CALLS_EXTERNAL", fn_node.id, target_id),
                    type="CALLS_EXTERNAL",
                    source=fn_node.id,
                    target=target_id,
                )
            )
            contract_name = self._call_contract_name(call)
            if contract_name:
                contract_node = self._get_or_create_contract_node(graph, contract_name)
                graph.add_edge(
                    Edge(
                        id=self._edge_id("CALLS_CONTRACT", fn_node.id, contract_node.id),
                        type="CALLS_CONTRACT",
                        source=fn_node.id,
                        target=contract_node.id,
                    )
                )
        for _, call in getattr(fn, "high_level_calls", []) or []:
            target_id = self._ensure_call_target(graph, call)
            graph.add_edge(
                Edge(
                    id=self._edge_id("CALLS_EXTERNAL", fn_node.id, target_id),
                    type="CALLS_EXTERNAL",
                    source=fn_node.id,
                    target=target_id,
                )
            )
            contract_name = self._call_contract_name(call)
            if contract_name:
                contract_node = self._get_or_create_contract_node(graph, contract_name)
                graph.add_edge(
                    Edge(
                        id=self._edge_id("CALLS_CONTRACT", fn_node.id, contract_node.id),
                        type="CALLS_CONTRACT",
                        source=fn_node.id,
                        target=contract_node.id,
                    )
                )

    def _ensure_call_target(self, graph: KnowledgeGraph, call: Any) -> str:
        name = (
            getattr(call, "name", None)
            or getattr(call, "full_name", None)
            or getattr(call, "function_name", None)
            or "external_call"
        )
        file_path, line_start, line_end = self._source_location(call)
        node_id = self._node_id("call", name, file_path, line_start)
        graph.add_node(
            Node(
                id=node_id,
                type="CallTarget",
                label=str(name),
                properties={
                    "file": file_path,
                    "line_start": line_start,
                    "line_end": line_end,
                },
                evidence=self._evidence(file_path, line_start, line_end),
            )
        )
        return node_id

    def _get_or_create_contract_node(self, graph: KnowledgeGraph, name: str) -> Node:
        for node in graph.nodes.values():
            if node.type == "Contract" and node.label == name:
                return node
        node_id = self._node_id("external_contract", name, "unknown", None)
        node = Node(
            id=node_id,
            type="ExternalContract",
            label=name,
            properties={"file": "unknown"},
        )
        graph.add_node(node)
        return node

    def _call_contract_name(self, call: Any) -> str | None:
        for attr in ("contract_name", "contract", "called_contract"):
            value = getattr(call, attr, None)
            if value is None:
                continue
            if isinstance(value, str):
                return value
            name = getattr(value, "name", None)
            if name:
                return str(name)
        destination = getattr(call, "destination", None)
        if destination is not None:
            destination_type = getattr(destination, "type", None)
            if destination_type is not None:
                dest_name = str(destination_type)
                if dest_name and dest_name != "address":
                    return dest_name
        name = getattr(call, "name", None) or getattr(call, "full_name", None)
        if not name:
            return None
        label = str(name)
        if "." in label:
            return label.split(".", 1)[0]
        return None

    def _external_call_contracts(
        self,
        external_calls: list[Any],
        high_level_calls: list[Any],
        contract_name: str,
    ) -> set[str]:
        targets: set[str] = set()
        for call in external_calls:
            target = self._call_contract_name(call)
            if not target:
                continue
            if target != contract_name:
                targets.add(target)
        for _, call in high_level_calls:
            target = self._call_contract_name(call)
            if not target:
                continue
            if target != contract_name:
                targets.add(target)
        return targets

    def _link_external_callsites(self, graph: KnowledgeGraph, fn: Any, fn_node: Node) -> None:
        low_level_calls = getattr(fn, "low_level_calls", []) or []
        if not low_level_calls:
            return
        for idx, call in enumerate(low_level_calls):
            call_file, call_start, call_end = self._callsite_location(call, fn_node)
            callsite_id = self._node_id("callsite", f"{fn_node.id}:{idx}", call_file, call_start)
            call_kind = self._callsite_kind(call)
            call_value = getattr(call, "call_value", None)
            call_gas = getattr(call, "call_gas", None)
            destination = self._callsite_destination(call)

            callsite_node = Node(
                id=callsite_id,
                type="ExternalCallSite",
                label=f"{call_kind}()",
                properties={
                    "call_kind": call_kind,
                    "has_call_value": call_value is not None,
                    "has_call_gas": call_gas is not None,
                    "destination": destination,
                    "file": call_file,
                    "line_start": call_start,
                    "line_end": call_end,
                },
                evidence=self._evidence(call_file, call_start, call_end),
            )
            graph.add_node(callsite_node)
            graph.add_edge(
                Edge(
                    id=self._edge_id("FUNCTION_HAS_CALLSITE", fn_node.id, callsite_id),
                    type="FUNCTION_HAS_CALLSITE",
                    source=fn_node.id,
                    target=callsite_id,
                )
            )

            if destination:
                target_id = self._node_id("calltarget", destination, call_file, call_start)
                graph.add_node(
                    Node(
                        id=target_id,
                        type="CallTarget",
                        label=destination,
                        properties={
                            "file": call_file,
                            "line_start": call_start,
                            "line_end": call_end,
                        },
                    )
                )
                graph.add_edge(
                    Edge(
                        id=self._edge_id("CALLSITE_TARGETS", callsite_id, target_id),
                        type="CALLSITE_TARGETS",
                        source=callsite_id,
                        target=target_id,
                    )
                )

            if call_value is not None:
                transfer_id = self._node_id(
                    "value_transfer",
                    f"{fn_node.id}:{idx}:value",
                    call_file,
                    call_start,
                )
                graph.add_node(
                    Node(
                        id=transfer_id,
                        type="ValueTransfer",
                        label="value",
                        properties={
                            "kind": "ETH",
                            "source": fn_node.label,
                            "file": call_file,
                            "line_start": call_start,
                            "line_end": call_end,
                        },
                    )
                )
                graph.add_edge(
                    Edge(
                        id=self._edge_id("CALLSITE_MOVES_VALUE", callsite_id, transfer_id),
                        type="CALLSITE_MOVES_VALUE",
                        source=callsite_id,
                        target=transfer_id,
                    )
                )

    def _callsite_kind(self, call: Any) -> str:
        name = getattr(call, "function_name", None) or getattr(call, "name", None)
        if name:
            return str(name)
        return "call"

    def _callsite_destination(self, call: Any) -> str | None:
        destination = getattr(call, "destination", None)
        if destination is None:
            return None
        name = getattr(destination, "name", None)
        if name:
            return str(name)
        return str(destination)

    def _callsite_location(self, call: Any, fn_node: Node) -> tuple[str | None, int | None, int | None]:
        expression = getattr(call, "expression", None)
        if expression is not None:
            return self._source_location(expression)
        return (
            fn_node.properties.get("file"),
            fn_node.properties.get("line_start"),
            fn_node.properties.get("line_end"),
        )

    def _link_signature_use(
        self,
        graph: KnowledgeGraph,
        *,
        fn_node: Node,
        uses_ecrecover: bool,
        uses_chainid: bool,
        has_nonce_parameter: bool,
    ) -> None:
        if not uses_ecrecover:
            return
        file_path = fn_node.properties.get("file")
        line_start = fn_node.properties.get("line_start")
        line_end = fn_node.properties.get("line_end")
        sig_id = self._node_id("signature", fn_node.id, file_path, line_start)
        graph.add_node(
            Node(
                id=sig_id,
                type="SignatureUse",
                label="ecrecover",
                properties={
                    "uses_chainid": uses_chainid,
                    "has_nonce_parameter": has_nonce_parameter,
                    "file": file_path,
                    "line_start": line_start,
                    "line_end": line_end,
                },
                evidence=self._evidence(file_path, line_start, line_end),
            )
        )
        graph.add_edge(
            Edge(
                id=self._edge_id("FUNCTION_USES_SIGNATURE", fn_node.id, sig_id),
                type="FUNCTION_USES_SIGNATURE",
                source=fn_node.id,
                target=sig_id,
            )
        )

    def _is_pre_08_pragma(self, file_text: str) -> bool:
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

    def _strip_comments(self, text: str) -> str:
        if not text:
            return ""
        no_line = re.sub(r"//.*", "", text)
        return re.sub(r"/\*.*?\*/", "", no_line, flags=re.DOTALL)

    def _uses_safemath(self, file_text: str) -> bool:
        return "safemath" in file_text.lower()

    def _has_uninitialized_storage_var(self, state_vars: list[Any]) -> bool:
        for var in state_vars:
            if getattr(var, "is_constant", False) or getattr(var, "is_immutable", False):
                continue
            expression = getattr(var, "expression", None) or getattr(var, "value", None)
            if expression is None:
                return True
        return False

    def _has_uninitialized_bool_var(self, state_vars: list[Any]) -> bool:
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

    def _has_diamond_inheritance(self, contract: Any) -> bool:
        bases = getattr(contract, "inheritance", []) or []
        if len(bases) < 2:
            return False
        for base in bases:
            if getattr(base, "inheritance", []) or []:
                return True
        return True

    def _has_shadowing(self, contract: Any) -> bool:
        state_vars = {getattr(var, "name", None) for var in getattr(contract, "state_variables", []) or []}
        state_vars.discard(None)
        if not state_vars:
            return False
        for fn in getattr(contract, "functions", []) or []:
            parameters = [getattr(p, "name", None) for p in getattr(fn, "parameters", []) or []]
            locals_ = [getattr(v, "name", None) for v in getattr(fn, "local_variables", []) or []]
            locals_ += [getattr(v, "name", None) for v in getattr(fn, "variables", []) or []]
            for name in parameters + locals_:
                if name and name in state_vars:
                    return True
        return False

    def _has_arithmetic_ops(self, source_text_lower: str) -> bool:
        return any(op in source_text_lower for op in ("+", "-", "*", "/"))

    def _has_division(self, source_text_lower: str) -> bool:
        return "/" in source_text_lower or ".div(" in source_text_lower

    def _has_multiplication(self, source_text_lower: str) -> bool:
        return "*" in source_text_lower or ".mul(" in source_text_lower

    def _division_before_multiplication(self, source_text_lower: str) -> bool:
        for line in source_text_lower.splitlines():
            if "/" in line and "*" in line and line.find("/") < line.find("*"):
                return True
        return False

    def _in_financial_context(
        self,
        source_text_lower: str,
        state_read_targets: dict[str, list[str]],
        state_write_targets: dict[str, list[str]],
    ) -> bool:
        tokens = (
            "fee",
            "reward",
            "share",
            "price",
            "rate",
            "interest",
            "yield",
            "swap",
            "deposit",
            "withdraw",
            "basis",
            "bps",
            "mint",
            "redeem",
        )
        if any(token in source_text_lower for token in tokens):
            return True
        for targets in (state_read_targets, state_write_targets):
            if self._has_state_tag(targets, "balance"):
                return True
            if self._has_state_tag(targets, "shares"):
                return True
            if self._has_state_tag(targets, "supply"):
                return True
            if self._has_state_tag(targets, "fee"):
                return True
        return False

    def _unchecked_uses_parameters(self, source_text_lower: str, parameter_names: list[str]) -> bool:
        if "unchecked" not in source_text_lower:
            return False
        for name in parameter_names:
            if name.lower() in source_text_lower:
                return True
        return False

    def _has_explicit_cast(self, source_text_lower: str) -> bool:
        return bool(re.search(r"\b(u?int\d*|address|bytes\d*|bool)\s*\(", source_text_lower))

    def _cast_is_narrowing(self, source_text_lower: str) -> bool:
        narrow = ("uint8(", "uint16(", "uint32(", "uint64(", "uint96(", "uint128(", "int8(", "int16(", "int32(")
        return any(token in source_text_lower for token in narrow)

    def _has_bounds_check_before_cast(self, require_exprs: list[str], parameter_names: list[str]) -> bool:
        if not require_exprs or not parameter_names:
            return False
        for expr in require_exprs:
            lowered = expr.lower()
            if not any(name.lower() in lowered for name in parameter_names):
                continue
            if "type(" in lowered or "max" in lowered:
                return True
            if any(op in lowered for op in ("<", "<=")) and re.search(r"\b\d+\b", lowered):
                return True
        return False

    def _has_signed_to_unsigned_cast(self, source_text_lower: str, parameter_types: list[str]) -> bool:
        has_signed_param = any(
            t.startswith("int") and not t.startswith("uint") for t in (p.lower() for p in parameter_types)
        )
        return has_signed_param and bool(re.search(r"\buint\d*\s*\(", source_text_lower))

    def _has_signed_check(self, require_exprs: list[str], parameter_names: list[str]) -> bool:
        for expr in require_exprs:
            lowered = expr.lower()
            if not any(name.lower() in lowered for name in parameter_names):
                continue
            if any(op in lowered for op in ("> 0", ">= 0", ">=")):
                return True
        return False

    def _has_address_to_uint_cast(self, source_text_lower: str, address_param_names: list[str]) -> bool:
        if not address_param_names:
            return False
        for name in address_param_names:
            if f"uint160({name.lower()}" in source_text_lower or f"uint({name.lower()}" in source_text_lower:
                return True
        return "uint160(" in source_text_lower and "address" in source_text_lower

    def _divisor_validated_nonzero(self, require_exprs: list[str], parameter_names: list[str]) -> bool:
        for expr in require_exprs:
            lowered = expr.lower()
            if not any(name.lower() in lowered for name in parameter_names):
                continue
            if "!=" in lowered or "> 0" in lowered or ">= 1" in lowered:
                return True
        return False

    def _has_rounding_ops(self, source_text_lower: str) -> bool:
        tokens = ("round", "truncate", "floor", "ceil")
        return any(token in source_text_lower for token in tokens)

    def _large_number_multiplication(self, source_text_lower: str) -> bool:
        if "*" not in source_text_lower and ".mul(" not in source_text_lower:
            return False
        return bool(re.search(r"1e\d+|10\s*\*\*\s*\d+", source_text_lower))

    def _price_amount_multiplication(self, source_text_lower: str) -> bool:
        if "price" not in source_text_lower or "amount" not in source_text_lower:
            return False
        return "*" in source_text_lower or ".mul(" in source_text_lower

    def _percentage_calculation(self, source_text_lower: str) -> bool:
        return "percent" in source_text_lower or "pct" in source_text_lower

    def _percentage_bounds_check(self, require_exprs: list[str], parameter_names: list[str]) -> bool:
        for expr in require_exprs:
            lowered = expr.lower()
            if "percent" not in lowered and "pct" not in lowered:
                continue
            if any(op in lowered for op in ("<=", "<", ">=", ">")):
                return True
        return False

    def _basis_points_calculation(self, source_text_lower: str) -> bool:
        return "bps" in source_text_lower or "basis" in source_text_lower

    def _ratio_calculation(self, source_text_lower: str) -> bool:
        return "ratio" in source_text_lower or "proportion" in source_text_lower

    def _fee_calculation(self, source_text_lower: str) -> bool:
        return "fee" in source_text_lower

    def _fee_accumulation(self, source_text_lower: str) -> bool:
        return "fee" in source_text_lower and ("+=" in source_text_lower or "totalfee" in source_text_lower)

    def _timestamp_arithmetic(self, source_text_lower: str) -> bool:
        if "block.timestamp" not in source_text_lower:
            return False
        return "+" in source_text_lower or "-" in source_text_lower

    def _uses_token_decimals(self, source_text_lower: str) -> bool:
        return "decimals" in source_text_lower

    def _decimal_scaling_usage(self, source_text_lower: str) -> bool:
        clean = self._strip_comments(source_text_lower)
        if "decimals" not in clean:
            return False
        return bool(re.search(r"1e\d+|10\s*\*\*\s*\d+", clean))

    def _has_decimal_normalization(self, source_text_lower: str) -> bool:
        clean = self._strip_comments(source_text_lower)
        if "decimals" not in clean:
            return False
        if "muldiv" in clean or "precisionfactor" in clean or "normalize" in clean:
            return True
        if re.search(r"/\s*10\s*\*\*\s*decimals", clean):
            return True
        if re.search(r"/\s*decimals\b", clean):
            return True
        return False

    def _uses_muldiv_or_safemath(self, source_text_lower: str) -> bool:
        return "muldiv" in source_text_lower or "safemath" in source_text_lower

    def _loop_counter_small_type(self, source_text_lower: str) -> bool:
        tokens = ("for (uint8", "for (uint16", "for (uint32", "for (uint64")
        return any(token in source_text_lower for token in tokens)

    def _state_machine_var_names(self, state_vars: list[Any]) -> list[str]:
        names = []
        for var in state_vars:
            name = getattr(var, "name", None)
            if not name:
                continue
            lowered = name.lower()
            if any(token in lowered for token in ("state", "status", "phase", "stage")):
                names.append(name)
        return names

    def _validates_current_state(self, require_exprs: list[str], state_machine_vars: list[str]) -> bool:
        if not state_machine_vars:
            return False
        for expr in require_exprs:
            lowered = expr.lower()
            if any(name.lower() in lowered for name in state_machine_vars) and any(
                op in lowered for op in ("==", "!=")
            ):
                return True
        return False

    def _state_cleanup_missing(self, source_text_lower: str) -> bool:
        cleanup_tokens = ("reset", "clear", "delete", "false", "0")
        return not any(token in source_text_lower for token in cleanup_tokens)

    def _state_race_condition(self, has_external_calls: bool, writes_state: bool, has_reentrancy_guard: bool) -> bool:
        return bool(has_external_calls and writes_state and not has_reentrancy_guard)

    def _double_counting_risk(self, source_text_lower: str, writes_balance_state: bool, writes_supply_state: bool) -> bool:
        if not (writes_balance_state and writes_supply_state):
            return False
        return "+=" in source_text_lower or "++" in source_text_lower

    def _event_param_mismatch(self, source_text_lower: str, parameter_names: list[str]) -> bool:
        if "emit " not in source_text_lower:
            return False
        emit_lines = [line for line in source_text_lower.splitlines() if "emit " in line]
        if not emit_lines:
            return False
        if not parameter_names:
            return True
        for line in emit_lines:
            if any(name.lower() in line for name in parameter_names):
                return False
        return True

    def _selfdestruct_target_user_controlled(self, source_text_lower: str, address_param_names: list[str]) -> bool:
        for line in source_text_lower.splitlines():
            if "selfdestruct" not in line:
                continue
            for name in address_param_names:
                if name.lower() in line:
                    return True
        return False

    def _share_inflation_risk(
        self,
        reads_share_state: bool,
        writes_share_state: bool,
        reads_supply_state: bool,
        uses_amount_division: bool,
        has_division: bool,
        has_precision_guard: bool,
        has_balance_check: bool,
    ) -> bool:
        if not (reads_share_state and writes_share_state and reads_supply_state):
            return False
        if not (uses_amount_division or has_division):
            return False
        return not (has_precision_guard or has_balance_check)

    def _source_location(self, obj: Any) -> tuple[str, int | None, int | None]:
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
        try:
            return str(Path(filename).resolve().relative_to(self.project_root.resolve()))
        except Exception:
            return str(filename)

    def _evidence(self, file_path: str | None, line_start: int | None, line_end: int | None) -> list[Evidence]:
        if not file_path or file_path == "unknown":
            return []
        return [Evidence(file=file_path, line_start=line_start, line_end=line_end)]

    def _node_id(self, kind: str, name: str, file_path: str | None, line_start: int | None) -> str:
        raw = f"{kind}:{name}:{file_path}:{line_start}"
        return f"{kind}:{hashlib.sha1(raw.encode('utf-8')).hexdigest()[:12]}"

    def _edge_id(self, edge_type: str, source: str, target: str) -> str:
        raw = f"{edge_type}:{source}:{target}"
        return f"edge:{hashlib.sha1(raw.encode('utf-8')).hexdigest()[:12]}"

    def _log_compile_error(self, target: Path, exc: Exception) -> None:
        message = str(exc)
        missing_imports = extract_missing_imports(message)
        if missing_imports:
            self.logger.error(
                "solc_missing_imports",
                target=str(target),
                missing=sorted(missing_imports),
            )
        self.logger.error("vkg_build_failed", target=str(target), error=message)

    # ==========================================================================
    # Phase 5: Rich Edge Generation
    # ==========================================================================

    def _generate_rich_edges(self, graph: KnowledgeGraph) -> None:
        """Generate RichEdge objects from function properties.

        Creates intelligent edges with:
        - Risk scores based on edge type and context
        - Pattern tags for vulnerability detection
        - Temporal ordering information
        - Guard analysis

        Args:
            graph: KnowledgeGraph to populate with rich edges
        """
        edge_counter = 0

        for fn_node in graph.nodes.values():
            if fn_node.type != "Function":
                continue

            props = fn_node.properties
            file_path = props.get("file")
            line_start = props.get("line_start")
            line_end = props.get("line_end")

            # Determine guards for this function
            guards = []
            if props.get("has_access_gate"):
                guards.append("access_control")
            if props.get("has_reentrancy_guard"):
                guards.append("reentrancy_guard")
            modifiers = props.get("modifiers") or []
            guards.extend(modifiers)

            # Check for CEI violation (write after external call)
            has_write_after_call = props.get("state_write_after_external_call", False)
            has_external_calls = props.get("has_external_calls", False)

            # Create rich edges for state writes
            state_vars_written = props.get("state_variables_written_names") or []
            for idx, var in enumerate(state_vars_written):
                edge_counter += 1
                is_critical = var in (props.get("critical_state_written") or []) or \
                    any(tag in ["owner", "admin", "role", "treasury"] for tag in props.get("security_tags", []))

                edge_type = EdgeType.WRITES_CRITICAL_STATE if is_critical else EdgeType.WRITES_STATE
                rich_edge = create_rich_edge(
                    edge_id=f"rich:{fn_node.id}:writes:{edge_counter}",
                    edge_type=edge_type,
                    source=fn_node.id,
                    target=f"state:{var}",
                    guards=guards if guards else None,
                    after_external_call=has_write_after_call,
                    file=file_path,
                    line_start=line_start,
                    line_end=line_end,
                )
                graph.add_rich_edge(rich_edge)

            # Create rich edges for external calls
            if has_external_calls:
                edge_counter += 1
                is_untrusted = props.get("has_untrusted_external_call", False)
                edge_type = EdgeType.CALLS_UNTRUSTED if is_untrusted else EdgeType.CALLS_EXTERNAL

                # Check for delegatecall
                exec_context = None
                if props.get("has_delegatecall"):
                    exec_context = ExecutionContext.DELEGATECALL.value
                    edge_type = EdgeType.DELEGATECALL

                rich_edge = create_rich_edge(
                    edge_id=f"rich:{fn_node.id}:calls:{edge_counter}",
                    edge_type=edge_type,
                    source=fn_node.id,
                    target=f"external_call:{fn_node.id}",
                    execution_context=exec_context,
                    guards=guards if guards else None,
                    file=file_path,
                    line_start=line_start,
                    line_end=line_end,
                )
                graph.add_rich_edge(rich_edge)

            # Create rich edges for value transfers
            if props.get("has_eth_transfer") or props.get("uses_native_transfer"):
                edge_counter += 1
                rich_edge = create_rich_edge(
                    edge_id=f"rich:{fn_node.id}:transfer:{edge_counter}",
                    edge_type=EdgeType.TRANSFERS_ETH,
                    source=fn_node.id,
                    target=f"eth_sink:{fn_node.id}",
                    guards=guards if guards else None,
                    transfers_value=True,
                    after_external_call=has_write_after_call,
                    file=file_path,
                    line_start=line_start,
                    line_end=line_end,
                )
                graph.add_rich_edge(rich_edge)

            # Create rich edges for token transfers
            if props.get("uses_erc20_transfer"):
                edge_counter += 1
                rich_edge = create_rich_edge(
                    edge_id=f"rich:{fn_node.id}:token:{edge_counter}",
                    edge_type=EdgeType.TRANSFERS_TOKEN,
                    source=fn_node.id,
                    target=f"token_sink:{fn_node.id}",
                    guards=guards if guards else None,
                    transfers_value=True,
                    file=file_path,
                    line_start=line_start,
                    line_end=line_end,
                )
                graph.add_rich_edge(rich_edge)

            # Create rich edges for oracle reads
            if props.get("reads_oracle_price"):
                edge_counter += 1
                has_staleness = props.get("has_staleness_check", False)
                taint = TaintSource.ORACLE.value if not has_staleness else None

                rich_edge = create_rich_edge(
                    edge_id=f"rich:{fn_node.id}:oracle:{edge_counter}",
                    edge_type=EdgeType.READS_ORACLE,
                    source=fn_node.id,
                    target=f"oracle:{fn_node.id}",
                    taint_source=taint,
                    file=file_path,
                    line_start=line_start,
                    line_end=line_end,
                )
                graph.add_rich_edge(rich_edge)

            # Create rich edges for user balance reads
            balance_vars_read = props.get("state_variables_read_names") or []
            for idx, var in enumerate(balance_vars_read):
                # Only track balance-related variables
                if any(keyword in var.lower() for keyword in ["balance", "amount", "deposit", "stake"]):
                    edge_counter += 1
                    rich_edge = create_rich_edge(
                        edge_id=f"rich:{fn_node.id}:readbal:{edge_counter}",
                        edge_type=EdgeType.READS_BALANCE,
                        source=fn_node.id,
                        target=f"state:{var}",
                        file=file_path,
                        line_start=line_start,
                        line_end=line_end,
                    )
                    graph.add_rich_edge(rich_edge)

        self.logger.debug(
            "rich_edges_generated",
            count=len(graph.rich_edges),
        )

    def _generate_meta_edges(self, graph: KnowledgeGraph) -> None:
        """Generate meta-edges for higher-order relationships.

        Creates:
        - SIMILAR_TO edges between similar functions
        - BUGGY_PATTERN_MATCH edges for vulnerability pattern matches

        Args:
            graph: KnowledgeGraph to populate with meta-edges
        """
        meta_edges = generate_meta_edges(graph)
        for meta_edge in meta_edges:
            graph.add_meta_edge(meta_edge)

        self.logger.debug(
            "meta_edges_generated",
            count=len(graph.meta_edges),
            similar_count=sum(1 for e in meta_edges if e.type == EdgeType.SIMILAR_TO),
            pattern_match_count=sum(1 for e in meta_edges if e.type == EdgeType.BUGGY_PATTERN_MATCH),
        )

    # ==========================================================================
    # Phase 6: Node Classification
    # ==========================================================================

    def _classify_nodes(self, graph: KnowledgeGraph) -> None:
        """Classify all nodes into semantic roles.

        Adds `semantic_role` and `atomic_blocks` properties to nodes:
        - Functions: Guardian, Checkpoint, EscapeHatch, EntryPoint, Internal, View
        - StateVariables: StateAnchor, CriticalState, ConfigState, InternalState

        Also detects atomic blocks (CEI regions) for functions with external calls.

        Args:
            graph: KnowledgeGraph to classify
        """
        classifier = NodeClassifier()
        function_roles: dict[str, int] = {}
        var_roles: dict[str, int] = {}
        total_atomic_blocks = 0
        cei_violations = 0

        for node in graph.nodes.values():
            if node.type == "Function":
                # Classify function
                role = classifier.classify_function(node)
                node.properties["semantic_role"] = role.value

                # Count roles
                function_roles[role.value] = function_roles.get(role.value, 0) + 1

                # Detect atomic blocks (CEI regions)
                blocks = detect_atomic_blocks(node)
                if blocks:
                    node.properties["atomic_blocks"] = [b.to_dict() for b in blocks]
                    total_atomic_blocks += len(blocks)
                    cei_violations += sum(1 for b in blocks if b.cei_violation)

            elif node.type == "StateVariable":
                # Classify state variable
                role = classifier.classify_state_variable(node)
                node.properties["semantic_role"] = role.value

                # Count roles
                var_roles[role.value] = var_roles.get(role.value, 0) + 1

        self.logger.debug(
            "nodes_classified",
            function_roles=function_roles,
            state_variable_roles=var_roles,
            atomic_blocks=total_atomic_blocks,
            cei_violations=cei_violations,
        )

    def _analyze_execution_paths(self, graph: KnowledgeGraph) -> None:
        """Analyze execution paths for multi-step vulnerability detection.

        Enumerates paths from public entry points and generates attack scenarios.
        Results are stored in graph.metadata['path_analysis'].

        Args:
            graph: KnowledgeGraph to analyze
        """
        try:
            # Get path analysis summary (limited depth for performance)
            summary = get_path_analysis_summary(graph)

            # Store in graph metadata
            graph.metadata["path_analysis"] = {
                "total_paths": summary.get("total_paths", 0),
                "attack_paths": summary.get("attack_paths", 0),
                "privilege_escalation_paths": summary.get("privilege_escalation_paths", 0),
                "total_scenarios": summary.get("total_scenarios", 0),
                "scenario_types": summary.get("scenario_types", {}),
                "entry_point_count": len(summary.get("entry_points", [])),
            }

            # Store highest risk path if available
            if summary.get("highest_risk_path"):
                highest = summary["highest_risk_path"]
                graph.metadata["path_analysis"]["highest_risk"] = {
                    "id": highest.get("id", ""),
                    "attack_potential": highest.get("attack_potential", 0),
                    "path_type": highest.get("path_type", "normal"),
                }

            self.logger.debug(
                "paths_analyzed",
                total_paths=summary.get("total_paths", 0),
                attack_paths=summary.get("attack_paths", 0),
                scenarios=summary.get("total_scenarios", 0),
            )

        except Exception as exc:
            # Path analysis is optional - log and continue
            self.logger.warning("path_analysis_failed", error=str(exc))
