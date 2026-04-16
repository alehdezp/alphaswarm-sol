"""Call tracking with confidence scoring for VKG builder.

This module provides call tracking functionality including:
- Internal call tracking (HIGH confidence)
- External call tracking (HIGH/MEDIUM/LOW based on resolution)
- Low-level call tracking (delegatecall, staticcall, call)
- Callback pattern detection with bidirectional edges
- Unresolved target tracking for completeness reporting

The CallTracker class produces confidence-scored edges and detects
callback patterns that require bidirectional edge creation.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from alphaswarm_sol.kg.builder.helpers import source_location, evidence_from_location
from alphaswarm_sol.kg.builder.types import (
    CallConfidence,
    CallInfo,
    CallType,
    CallbackPattern,
    TargetResolution,
    UnresolvedTarget,
)
from alphaswarm_sol.kg.schema import Edge, Node

if TYPE_CHECKING:
    from alphaswarm_sol.kg.builder.context import BuildContext
    from alphaswarm_sol.kg.schema import KnowledgeGraph


# -----------------------------------------------------------------------------
# Known Callback Patterns
# -----------------------------------------------------------------------------

CALLBACK_PATTERNS: dict[str, list[str]] = {
    # Flash loan patterns
    "flashLoan": ["onFlashLoan", "executeOperation"],
    "flash": ["uniswapV2Call", "uniswapV3FlashCallback", "pancakeCall"],
    "flashLoanSimple": ["executeOperation"],
    "executeOperation": [],  # Already a callback
    # Uniswap/DEX patterns
    "swap": ["uniswapV2Call", "uniswapV3SwapCallback"],
    "uniswapV2Call": [],  # Already a callback
    "uniswapV3SwapCallback": [],  # Already a callback
    "pancakeCall": [],  # Already a callback
    # ERC721 patterns
    "safeTransferFrom": ["onERC721Received"],
    "safeMint": ["onERC721Received"],
    "_safeMint": ["onERC721Received"],
    "_safeTransfer": ["onERC721Received"],
    # ERC1155 patterns
    "safeTransferFrom": ["onERC1155Received"],
    "safeBatchTransferFrom": ["onERC1155BatchReceived"],
    "_safeBatchTransferFrom": ["onERC1155BatchReceived"],
    # ERC777 patterns
    "transfer": ["tokensReceived", "tokensToSend"],
    "send": ["tokensReceived", "tokensToSend"],
    "_callTokensToSend": [],  # Internal helper
    "_callTokensReceived": [],  # Internal helper
    # Compound/lending patterns
    "borrow": ["executeOperation"],
    "liquidateBorrow": [],
    # Maker patterns
    "execute": ["exec"],
    # Generic callback patterns
    "call": [],  # Low-level, no known callback
    "delegatecall": [],  # Low-level, no known callback
    "staticcall": [],  # Read-only, no callback
}

# Callback function patterns for detection
CALLBACK_FUNCTION_NAMES: set[str] = {
    # Flash loan callbacks
    "onFlashLoan",
    "executeOperation",
    "uniswapV2Call",
    "uniswapV3FlashCallback",
    "uniswapV3SwapCallback",
    "pancakeCall",
    # ERC721 callbacks
    "onERC721Received",
    # ERC1155 callbacks
    "onERC1155Received",
    "onERC1155BatchReceived",
    # ERC777 callbacks
    "tokensReceived",
    "tokensToSend",
    # Generic
    "fallback",
    "receive",
}


# -----------------------------------------------------------------------------
# CallTracker Class
# -----------------------------------------------------------------------------

@dataclass
class CallTracker:
    """Tracks calls with confidence scoring and callback detection.

    The CallTracker analyzes function calls and produces:
    - Edges with confidence scores (HIGH/MEDIUM/LOW)
    - Bidirectional edges for detected callback patterns
    - Unresolved target tracking for completeness reporting

    Attributes:
        ctx: Build context for shared state and utilities.
        graph: Knowledge graph being constructed.
        _detected_callbacks: Accumulated callback patterns.
    """

    ctx: BuildContext
    graph: KnowledgeGraph
    _detected_callbacks: list[CallbackPattern] = field(default_factory=list)

    def track_all(self, fn: Any, fn_node: Node) -> list[Edge]:
        """Track all calls from a function.

        Args:
            fn: Slither function object.
            fn_node: The function's node in the graph.

        Returns:
            List of edges created for all calls.
        """
        edges: list[Edge] = []

        # Track internal calls (always HIGH confidence)
        edges.extend(self._track_internal_calls(fn, fn_node))

        # Track external calls (confidence varies)
        edges.extend(self._track_external_calls(fn, fn_node))

        # Track high-level calls
        edges.extend(self._track_high_level_calls(fn, fn_node))

        # Track low-level calls (usually LOW confidence)
        edges.extend(self._track_low_level_calls(fn, fn_node))

        # Detect and create callback edges
        edges.extend(self._create_callback_edges(fn, fn_node))

        return edges

    def _track_internal_calls(self, fn: Any, fn_node: Node) -> list[Edge]:
        """Track internal function calls with HIGH confidence.

        Internal calls have known targets within the same contract.

        Args:
            fn: Slither function object.
            fn_node: The function's node in the graph.

        Returns:
            List of CALLS_INTERNAL edges.
        """
        edges: list[Edge] = []
        internal_calls = getattr(fn, "internal_calls", []) or []

        for call in internal_calls:
            call_info = self._resolve_internal_call(call, fn)

            # Create or get target node
            target_id = self._ensure_call_target(call, call_info)

            edge_id = self.ctx.edge_id("CALLS_INTERNAL", fn_node.id, target_id)
            edge = Edge(
                id=edge_id,
                type="CALLS_INTERNAL",
                source=fn_node.id,
                target=target_id,
                properties={
                    "confidence": call_info.confidence,
                    "resolution": call_info.resolution,
                    "call_type": call_info.call_type,
                },
            )
            self.graph.add_edge(edge)
            edges.append(edge)

        return edges

    def _track_external_calls(self, fn: Any, fn_node: Node) -> list[Edge]:
        """Track external calls with confidence based on resolution.

        Args:
            fn: Slither function object.
            fn_node: The function's node in the graph.

        Returns:
            List of CALLS_EXTERNAL edges.
        """
        edges: list[Edge] = []
        external_calls = getattr(fn, "external_calls", []) or []

        for call in external_calls:
            call_info = self._resolve_external_call(call, fn)

            # Create or get target node
            target_id = self._ensure_call_target(call, call_info)

            edge_id = self.ctx.edge_id("CALLS_EXTERNAL", fn_node.id, target_id)
            edge = Edge(
                id=edge_id,
                type="CALLS_EXTERNAL",
                source=fn_node.id,
                target=target_id,
                properties={
                    "confidence": call_info.confidence,
                    "resolution": call_info.resolution,
                    "call_type": call_info.call_type,
                    "value_sent": call_info.value_sent,
                },
            )
            self.graph.add_edge(edge)
            edges.append(edge)

            # Create CALLS_CONTRACT edge if we know the contract
            if call_info.target_contract:
                contract_edge = self._create_contract_edge(fn_node, call_info)
                if contract_edge:
                    edges.append(contract_edge)

            # Check for callback patterns
            self._detect_callback_pattern(fn, fn_node, call, call_info)

        return edges

    def _track_high_level_calls(self, fn: Any, fn_node: Node) -> list[Edge]:
        """Track high-level external calls.

        High-level calls are provided as (contract, function) pairs by Slither.

        Args:
            fn: Slither function object.
            fn_node: The function's node in the graph.

        Returns:
            List of CALLS_EXTERNAL edges.
        """
        edges: list[Edge] = []
        high_level_calls = getattr(fn, "high_level_calls", []) or []

        for contract, call in high_level_calls:
            call_info = self._resolve_high_level_call(contract, call, fn)

            # Create or get target node
            target_id = self._ensure_call_target(call, call_info)

            edge_id = self.ctx.edge_id("CALLS_EXTERNAL", fn_node.id, target_id)
            edge = Edge(
                id=edge_id,
                type="CALLS_EXTERNAL",
                source=fn_node.id,
                target=target_id,
                properties={
                    "confidence": call_info.confidence,
                    "resolution": call_info.resolution,
                    "call_type": call_info.call_type,
                    "value_sent": call_info.value_sent,
                },
            )
            self.graph.add_edge(edge)
            edges.append(edge)

            # Create CALLS_CONTRACT edge
            if call_info.target_contract:
                contract_edge = self._create_contract_edge(fn_node, call_info)
                if contract_edge:
                    edges.append(contract_edge)

            # Check for callback patterns
            self._detect_callback_pattern(fn, fn_node, call, call_info)

        return edges

    def _track_low_level_calls(self, fn: Any, fn_node: Node) -> list[Edge]:
        """Track low-level calls (call, delegatecall, staticcall).

        Low-level calls typically have LOW confidence unless we can
        analyze the destination expression.

        Args:
            fn: Slither function object.
            fn_node: The function's node in the graph.

        Returns:
            List of edges for low-level call sites.
        """
        edges: list[Edge] = []
        low_level_calls = getattr(fn, "low_level_calls", []) or []

        for idx, call in enumerate(low_level_calls):
            call_info = self._resolve_low_level_call(call, fn)

            # Create callsite node
            file_path, line_start, line_end = self._callsite_location(call, fn_node)
            callsite_id = self.ctx.node_id(
                "callsite",
                fn_node.label,
                f"{idx}",
                f"{fn_node.id}:{idx}",
            )

            call_kind = self._callsite_kind(call)
            destination = self._callsite_destination(call)
            call_value = getattr(call, "call_value", None)
            call_gas = getattr(call, "call_gas", None)

            callsite_node = Node(
                id=callsite_id,
                type="ExternalCallSite",
                label=f"{call_kind}()",
                properties={
                    "call_kind": call_kind,
                    "confidence": call_info.confidence,
                    "resolution": call_info.resolution,
                    "has_call_value": call_value is not None,
                    "has_call_gas": call_gas is not None,
                    "destination": destination,
                    "file": file_path,
                    "line_start": line_start,
                    "line_end": line_end,
                },
                evidence=evidence_from_location(file_path, line_start, line_end),
            )
            self.graph.add_node(callsite_node)

            # Edge from function to callsite
            callsite_edge = Edge(
                id=self.ctx.edge_id("FUNCTION_HAS_CALLSITE", fn_node.id, callsite_id),
                type="FUNCTION_HAS_CALLSITE",
                source=fn_node.id,
                target=callsite_id,
                properties={
                    "confidence": call_info.confidence,
                    "call_type": call_info.call_type,
                },
            )
            self.graph.add_edge(callsite_edge)
            edges.append(callsite_edge)

            # If we have a destination, create target node and edge
            if destination:
                target_id = self.ctx.node_id(
                    "calltarget",
                    destination,
                    destination,
                    f"{file_path}:{line_start}",
                )
                self.graph.add_node(
                    Node(
                        id=target_id,
                        type="CallTarget",
                        label=destination,
                        properties={
                            "confidence": call_info.confidence,
                            "file": file_path,
                            "line_start": line_start,
                            "line_end": line_end,
                        },
                    )
                )
                target_edge = Edge(
                    id=self.ctx.edge_id("CALLSITE_TARGETS", callsite_id, target_id),
                    type="CALLSITE_TARGETS",
                    source=callsite_id,
                    target=target_id,
                    properties={"confidence": call_info.confidence},
                )
                self.graph.add_edge(target_edge)
                edges.append(target_edge)

            # Value transfer node for call.value
            if call_value is not None:
                transfer_id = self.ctx.node_id(
                    "value_transfer",
                    f"{fn_node.id}:{idx}:value",
                    "value",
                    f"{file_path}:{line_start}",
                )
                self.graph.add_node(
                    Node(
                        id=transfer_id,
                        type="ValueTransfer",
                        label="value",
                        properties={
                            "kind": "ETH",
                            "source": fn_node.label,
                            "file": file_path,
                            "line_start": line_start,
                            "line_end": line_end,
                        },
                    )
                )
                value_edge = Edge(
                    id=self.ctx.edge_id("CALLSITE_MOVES_VALUE", callsite_id, transfer_id),
                    type="CALLSITE_MOVES_VALUE",
                    source=callsite_id,
                    target=transfer_id,
                )
                self.graph.add_edge(value_edge)
                edges.append(value_edge)

        return edges

    # -------------------------------------------------------------------------
    # Resolution Methods
    # -------------------------------------------------------------------------

    def _resolve_internal_call(self, call: Any, fn: Any) -> CallInfo:
        """Resolve an internal call target.

        Internal calls are within the same contract, so they have
        HIGH confidence by default.

        Args:
            call: Slither call object.
            fn: The calling function.

        Returns:
            CallInfo with resolution details.
        """
        file_path, line_number, _ = source_location(call)

        target_name = (
            getattr(call, "name", None)
            or getattr(call, "full_name", None)
            or "unknown"
        )
        target_contract = self._get_contract_name(fn)

        return CallInfo(
            call_type="internal",
            target_contract=target_contract,
            target_function=str(target_name),
            confidence="HIGH",
            resolution="direct",
            file_path=file_path,
            line_number=line_number,
        )

    def _resolve_external_call(self, call: Any, fn: Any) -> CallInfo:
        """Resolve an external call target with confidence scoring.

        Confidence is based on how precisely we can determine the target:
        - HIGH: Direct contract reference (token.transfer())
        - MEDIUM: Interface type or state variable (IERC20(token).transfer())
        - LOW: Dynamic/unresolved target

        Args:
            call: Slither call object.
            fn: The calling function.

        Returns:
            CallInfo with resolution details.
        """
        file_path, line_number, _ = source_location(call)

        target_contract = self._call_contract_name(call)
        target_function = self._call_function_name(call)

        # Determine confidence and resolution
        confidence: CallConfidence
        resolution: TargetResolution

        if target_contract:
            # Check if target is an interface
            if self._is_interface(target_contract):
                confidence = "MEDIUM"
                resolution = "interface"
            else:
                confidence = "HIGH"
                resolution = "direct"
        else:
            confidence = "LOW"
            resolution = "unresolved"
            # Track unresolved target
            self._track_unresolved(
                fn,
                call,
                "external",
                "unknown_contract",
            )

        # Check for value sent
        value_sent = self._has_value_sent(call)

        return CallInfo(
            call_type="external",
            target_contract=target_contract,
            target_function=target_function,
            confidence=confidence,
            resolution=resolution,
            file_path=file_path,
            line_number=line_number,
            value_sent=value_sent,
        )

    def _resolve_high_level_call(
        self,
        contract: Any,
        call: Any,
        fn: Any,
    ) -> CallInfo:
        """Resolve a high-level call (contract, function) pair.

        High-level calls from Slither include the target contract,
        giving us better resolution than raw external calls.

        Args:
            contract: Slither contract object for the target.
            call: Slither function/call object.
            fn: The calling function.

        Returns:
            CallInfo with resolution details.
        """
        file_path, line_number, _ = source_location(call)

        # Get contract name from the provided contract object
        target_contract = getattr(contract, "name", None)
        if target_contract is None:
            target_contract = str(contract) if contract else None

        target_function = self._call_function_name(call)

        # Determine confidence based on contract type
        confidence: CallConfidence
        resolution: TargetResolution

        if target_contract:
            is_interface = getattr(contract, "is_interface", False)
            is_library = getattr(contract, "is_library", False)

            if is_library:
                confidence = "HIGH"
                resolution = "direct"
            elif is_interface:
                confidence = "MEDIUM"
                resolution = "interface"
            else:
                confidence = "HIGH"
                resolution = "direct"
        else:
            confidence = "LOW"
            resolution = "unresolved"
            self._track_unresolved(fn, call, "high_level", "unknown_contract")

        value_sent = self._has_value_sent(call)

        return CallInfo(
            call_type="library" if getattr(contract, "is_library", False) else "external",
            target_contract=target_contract,
            target_function=target_function,
            confidence=confidence,
            resolution=resolution,
            file_path=file_path,
            line_number=line_number,
            value_sent=value_sent,
        )

    def _resolve_low_level_call(self, call: Any, fn: Any) -> CallInfo:
        """Resolve a low-level call (call, delegatecall, staticcall).

        Low-level calls typically have LOW confidence as the target
        is often dynamic. We can sometimes infer from the destination.

        Args:
            call: Slither low-level call object.
            fn: The calling function.

        Returns:
            CallInfo with resolution details.
        """
        file_path, line_number, _ = source_location(call)

        # Determine call type
        call_kind = self._callsite_kind(call)
        call_type: CallType = "external"
        if call_kind == "delegatecall":
            call_type = "delegatecall"
        elif call_kind == "staticcall":
            call_type = "staticcall"

        # Try to resolve destination
        destination = self._callsite_destination(call)
        target_contract: str | None = None
        target_function: str | None = None
        confidence: CallConfidence = "LOW"
        resolution: TargetResolution = "unresolved"

        if destination:
            # Check if destination has a type we can analyze
            dest_type = self._get_destination_type(call)
            if dest_type and dest_type != "address":
                target_contract = dest_type
                confidence = "MEDIUM"
                resolution = "inferred"
            else:
                # Track as unresolved
                self._track_unresolved(fn, call, call_type, "dynamic_destination")

        call_value = getattr(call, "call_value", None)
        call_gas = getattr(call, "call_gas", None)

        return CallInfo(
            call_type=call_type,
            target_contract=target_contract,
            target_function=target_function,
            confidence=confidence,
            resolution=resolution,
            file_path=file_path,
            line_number=line_number,
            gas_specified=call_gas is not None,
            value_sent=call_value is not None,
        )

    # -------------------------------------------------------------------------
    # Callback Detection
    # -------------------------------------------------------------------------

    def _detect_callback_pattern(
        self,
        fn: Any,
        fn_node: Node,
        call: Any,
        call_info: CallInfo,
    ) -> None:
        """Detect if a call triggers a callback pattern.

        Checks known callback patterns (flash loans, ERC777, etc.)
        and records any detected patterns.

        Args:
            fn: Slither function object.
            fn_node: The function's node in the graph.
            call: The call being analyzed.
            call_info: Resolved call information.
        """
        if not call_info.target_function:
            return

        # Check if this function call has known callbacks
        callbacks = CALLBACK_PATTERNS.get(call_info.target_function, [])
        if not callbacks:
            return

        # Determine pattern type
        pattern_type = self._classify_callback_pattern(call_info.target_function)

        # Check if the calling contract implements any callback
        contract_name = self._get_contract_name(fn)
        contract = self.ctx.contract_cache.get(contract_name)
        if not contract:
            return

        contract_functions = {
            getattr(f, "name", ""): f
            for f in getattr(contract, "functions", [])
        }

        for callback_name in callbacks:
            if callback_name in contract_functions:
                callback_pattern = CallbackPattern(
                    source_function=fn_node.label,
                    callback_interface=call_info.target_contract or "unknown",
                    callback_function=callback_name,
                    pattern_type=pattern_type,
                    confidence=call_info.confidence,
                )
                self._detected_callbacks.append(callback_pattern)
                call_info.is_callback_source = True
                call_info.potential_callbacks.append(callback_name)

    def _create_callback_edges(self, fn: Any, fn_node: Node) -> list[Edge]:
        """Create bidirectional edges for detected callbacks.

        For each detected callback pattern, creates a CALLBACK_FROM edge
        from the external target back to the callback function.

        Args:
            fn: Slither function object.
            fn_node: The function's node in the graph.

        Returns:
            List of CALLBACK_FROM edges.
        """
        edges: list[Edge] = []

        contract_name = self._get_contract_name(fn)
        contract = self.ctx.contract_cache.get(contract_name)
        if not contract:
            return edges

        for pattern in self._detected_callbacks:
            # Find the callback function node
            callback_node = self._find_function_node(
                contract_name,
                pattern.callback_function,
            )
            if not callback_node:
                continue

            # Create callback edge (external -> callback)
            edge_id = self.ctx.edge_id(
                "CALLBACK_FROM",
                fn_node.id,  # Source is the function making the external call
                callback_node,  # Target is the callback function
            )
            edge = Edge(
                id=edge_id,
                type="CALLBACK_FROM",
                source=fn_node.id,
                target=callback_node,
                properties={
                    "callback_type": pattern.pattern_type,
                    "external_target": pattern.callback_interface,
                    "confidence": pattern.confidence,
                },
            )
            self.graph.add_edge(edge)
            edges.append(edge)

        # Clear detected callbacks for next function
        self._detected_callbacks.clear()

        return edges

    def _classify_callback_pattern(self, function_name: str) -> str:
        """Classify the type of callback pattern.

        Args:
            function_name: Name of the function triggering the callback.

        Returns:
            Pattern type string.
        """
        if function_name in ("flashLoan", "flash", "flashLoanSimple"):
            return "flash_loan"
        if function_name in ("swap",):
            return "uniswap"
        if function_name in ("safeTransferFrom", "safeMint", "_safeMint"):
            return "erc721"
        if function_name in ("transfer", "send"):
            return "erc777"
        if function_name in ("safeBatchTransferFrom",):
            return "erc1155"
        return "custom"

    # -------------------------------------------------------------------------
    # Helper Methods
    # -------------------------------------------------------------------------

    def _ensure_call_target(self, call: Any, call_info: CallInfo) -> str:
        """Ensure a call target node exists in the graph.

        Args:
            call: Slither call object.
            call_info: Resolved call information.

        Returns:
            Node ID of the call target.
        """
        name = call_info.target_function or "external_call"
        contract = call_info.target_contract or "unknown"

        node_id = self.ctx.node_id(
            "call",
            contract,
            name,
            f"{call_info.file_path}:{call_info.line_number}",
        )

        # Check if node already exists
        if node_id in self.graph.nodes:
            return node_id

        self.graph.add_node(
            Node(
                id=node_id,
                type="CallTarget",
                label=f"{contract}.{name}" if contract != "unknown" else name,
                properties={
                    "contract": contract,
                    "function": name,
                    "confidence": call_info.confidence,
                    "resolution": call_info.resolution,
                    "file": call_info.file_path,
                    "line_start": call_info.line_number,
                },
                evidence=evidence_from_location(
                    call_info.file_path,
                    call_info.line_number,
                    call_info.line_number,
                ),
            )
        )
        return node_id

    def _create_contract_edge(
        self,
        fn_node: Node,
        call_info: CallInfo,
    ) -> Edge | None:
        """Create a CALLS_CONTRACT edge if contract is known.

        Args:
            fn_node: The calling function's node.
            call_info: Resolved call information.

        Returns:
            Edge if contract is known, None otherwise.
        """
        if not call_info.target_contract:
            return None

        contract_node = self._get_or_create_contract_node(call_info.target_contract)
        edge_id = self.ctx.edge_id("CALLS_CONTRACT", fn_node.id, contract_node.id)

        edge = Edge(
            id=edge_id,
            type="CALLS_CONTRACT",
            source=fn_node.id,
            target=contract_node.id,
            properties={
                "confidence": call_info.confidence,
            },
        )
        self.graph.add_edge(edge)
        return edge

    def _get_or_create_contract_node(self, name: str) -> Node:
        """Get or create a contract node by name.

        Args:
            name: Contract name.

        Returns:
            The contract node (existing or newly created).
        """
        # Check if contract node already exists
        for node in self.graph.nodes.values():
            if node.type == "Contract" and node.label == name:
                return node

        # Create external contract node
        node_id = self.ctx.node_id("external_contract", name, name)
        node = Node(
            id=node_id,
            type="ExternalContract",
            label=name,
            properties={"file": "unknown"},
        )
        self.graph.add_node(node)
        return node

    def _call_contract_name(self, call: Any) -> str | None:
        """Extract contract name from a call object.

        Args:
            call: Slither call object.

        Returns:
            Contract name if determinable, None otherwise.
        """
        # Try direct attributes
        for attr in ("contract_name", "contract", "called_contract"):
            value = getattr(call, attr, None)
            if value is None:
                continue
            if isinstance(value, str):
                return value
            name = getattr(value, "name", None)
            if name:
                return str(name)

        # Try destination type
        destination = getattr(call, "destination", None)
        if destination is not None:
            destination_type = getattr(destination, "type", None)
            if destination_type is not None:
                dest_name = str(destination_type)
                if dest_name and dest_name != "address":
                    return dest_name

        # Try parsing from full name
        name = getattr(call, "name", None) or getattr(call, "full_name", None)
        if not name:
            return None
        label = str(name)
        if "." in label:
            return label.split(".", 1)[0]

        return None

    def _call_function_name(self, call: Any) -> str | None:
        """Extract function name from a call object.

        Args:
            call: Slither call object.

        Returns:
            Function name if determinable, None otherwise.
        """
        name = (
            getattr(call, "name", None)
            or getattr(call, "full_name", None)
            or getattr(call, "function_name", None)
        )
        if name:
            label = str(name)
            if "." in label:
                return label.split(".", 1)[1]
            return label
        return None

    def _get_contract_name(self, fn: Any) -> str:
        """Get the contract name for a function.

        Args:
            fn: Slither function object.

        Returns:
            Contract name.
        """
        contract = getattr(fn, "contract", None)
        if contract:
            return getattr(contract, "name", "unknown")
        return "unknown"

    def _is_interface(self, name: str) -> bool:
        """Check if a contract name is an interface.

        Args:
            name: Contract name.

        Returns:
            True if likely an interface.
        """
        # Check cache
        contract = self.ctx.contract_cache.get(name)
        if contract:
            return getattr(contract, "is_interface", False)

        # Heuristic: interfaces often start with 'I'
        return name.startswith("I") and len(name) > 1 and name[1].isupper()

    def _has_value_sent(self, call: Any) -> bool:
        """Check if a call sends value.

        Args:
            call: Slither call object.

        Returns:
            True if value is sent with the call.
        """
        return getattr(call, "call_value", None) is not None

    def _get_destination_type(self, call: Any) -> str | None:
        """Get the type of a call destination.

        Args:
            call: Slither call object.

        Returns:
            Type name if determinable.
        """
        destination = getattr(call, "destination", None)
        if destination is None:
            return None
        dest_type = getattr(destination, "type", None)
        if dest_type is not None:
            return str(dest_type)
        return None

    def _track_unresolved(
        self,
        fn: Any,
        call: Any,
        call_type: str,
        reason: str,
    ) -> None:
        """Track an unresolved call target.

        Args:
            fn: Slither function object.
            call: The call object.
            call_type: Type of call.
            reason: Why resolution failed.
        """
        file_path, line, _ = source_location(call)
        fn_name = getattr(fn, "canonical_name", None) or getattr(fn, "full_name", "unknown")
        target_expr = str(call) if call else "unknown"

        self.ctx.add_unresolved(
            UnresolvedTarget(
                source_function=str(fn_name),
                call_type=call_type,
                target_expression=target_expr,
                reason=reason,
                confidence="LOW",
                file=file_path,
                line=line,
            )
        )

    def _find_function_node(self, contract_name: str, function_name: str) -> str | None:
        """Find a function node by contract and function name.

        Args:
            contract_name: Name of the contract.
            function_name: Name of the function.

        Returns:
            Node ID if found, None otherwise.
        """
        for node_id, node in self.graph.nodes.items():
            if node.type != "Function":
                continue
            if node.label == function_name or node.label == f"{contract_name}.{function_name}":
                if contract_name in node_id:
                    return node_id
        return None

    def _callsite_kind(self, call: Any) -> str:
        """Get the kind of low-level call.

        Args:
            call: Slither low-level call object.

        Returns:
            Call kind: 'call', 'delegatecall', or 'staticcall'.
        """
        name = getattr(call, "function_name", None) or getattr(call, "name", None)
        if name:
            return str(name)
        return "call"

    def _callsite_destination(self, call: Any) -> str | None:
        """Get the destination of a low-level call.

        Args:
            call: Slither low-level call object.

        Returns:
            Destination string if determinable.
        """
        destination = getattr(call, "destination", None)
        if destination is None:
            return None
        name = getattr(destination, "name", None)
        if name:
            return str(name)
        return str(destination)

    def _callsite_location(
        self,
        call: Any,
        fn_node: Node,
    ) -> tuple[str | None, int | None, int | None]:
        """Get the source location of a callsite.

        Args:
            call: Slither call object.
            fn_node: The function node (fallback location).

        Returns:
            Tuple of (file_path, line_start, line_end).
        """
        expression = getattr(call, "expression", None)
        if expression is not None:
            return source_location(expression)
        return (
            fn_node.properties.get("file"),
            fn_node.properties.get("line_start"),
            fn_node.properties.get("line_end"),
        )

    def get_detected_callbacks(self) -> list[CallbackPattern]:
        """Get all detected callback patterns.

        Returns:
            List of CallbackPattern objects.
        """
        return list(self._detected_callbacks)


# -----------------------------------------------------------------------------
# Convenience Functions
# -----------------------------------------------------------------------------

def track_calls(
    ctx: BuildContext,
    graph: KnowledgeGraph,
    fn: Any,
    fn_node: Node,
) -> list[Edge]:
    """Track all calls from a function.

    Convenience function that creates a CallTracker and tracks all calls.

    Args:
        ctx: Build context.
        graph: Knowledge graph being constructed.
        fn: Slither function object.
        fn_node: The function's node in the graph.

    Returns:
        List of edges created.
    """
    tracker = CallTracker(ctx=ctx, graph=graph)
    return tracker.track_all(fn, fn_node)


def get_external_call_contracts(
    external_calls: list[Any],
    high_level_calls: list[Any],
    contract_name: str,
) -> set[str]:
    """Get the set of external contracts called by a function.

    Args:
        external_calls: List of external call objects.
        high_level_calls: List of (contract, function) pairs.
        contract_name: Name of the calling contract (to exclude self).

    Returns:
        Set of external contract names.
    """
    targets: set[str] = set()

    # Helper to extract contract name
    def extract_contract(call: Any) -> str | None:
        for attr in ("contract_name", "contract", "called_contract"):
            value = getattr(call, attr, None)
            if value is None:
                continue
            if isinstance(value, str):
                return value
            name = getattr(value, "name", None)
            if name:
                return str(name)
        return None

    for call in external_calls:
        target = extract_contract(call)
        if target and target != contract_name:
            targets.add(target)

    for contract, _ in high_level_calls:
        target = getattr(contract, "name", None)
        if target and target != contract_name:
            targets.add(target)

    return targets
