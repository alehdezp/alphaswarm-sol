"""Red Team Agent for MCTS-style attack synthesis.

Per 05.11-08-PLAN.md: Red Agent synthesizes attacks using MCTS-style exploration
with economic pruning via GATE. Generates AttackPlans with exploit paths,
expected profit, and success probability.

Key Features:
- MCTS-inspired exploration: UCB1 selection, LLM move generation
- Economic pruning: Prunes branches where attack EV < 0
- Integration with GATE for attack viability scoring
- Integration with CEG for causal path structure

Usage:
    from alphaswarm_sol.agents.adversarial.red_agent import (
        RedAgent,
        AttackPlan,
        ExploitPath,
        MCTSConfig,
    )

    agent = RedAgent()
    plan = agent.synthesize_attack(
        finding={"id": "vuln-1", "severity": "high"},
        protocol_state={"tvl_usd": 10_000_000},
        budget=MCTSConfig(max_iterations=100),
    )

    if plan.expected_profit > 0:
        print(f"Viable attack: EV=${plan.expected_profit:,.2f}")
        for step in plan.exploit_path:
            print(f"  Step {step.order}: {step.action}")
"""

from __future__ import annotations

import hashlib
import logging
import math
import random
from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# =============================================================================
# Transaction and Path Types
# =============================================================================


class TransactionType(Enum):
    """Types of transactions in an exploit path."""

    CALL = "call"  # Regular function call
    FLASH_LOAN_BORROW = "flash_loan_borrow"  # Flash loan initiation
    FLASH_LOAN_REPAY = "flash_loan_repay"  # Flash loan repayment
    SWAP = "swap"  # Token swap
    DEPOSIT = "deposit"  # Deposit funds
    WITHDRAW = "withdraw"  # Withdraw funds
    APPROVE = "approve"  # Token approval
    TRANSFER = "transfer"  # Token transfer
    CALLBACK = "callback"  # Reentrancy callback
    GOVERNANCE = "governance"  # Governance action
    ORACLE_MANIPULATION = "oracle_manipulation"  # Oracle price manipulation


@dataclass
class Transaction:
    """A single transaction in an exploit path.

    Attributes:
        order: Order in the exploit sequence
        tx_type: Type of transaction
        action: Human-readable action description
        target_contract: Contract being called
        function_name: Function being called
        parameters: Function parameters
        value_wei: ETH value sent with transaction
        gas_estimate: Estimated gas cost
        evidence_refs: Evidence supporting this transaction
        metadata: Additional metadata
    """

    order: int
    tx_type: TransactionType
    action: str
    target_contract: str = ""
    function_name: str = ""
    parameters: Dict[str, Any] = field(default_factory=dict)
    value_wei: int = 0
    gas_estimate: int = 100_000
    evidence_refs: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "order": self.order,
            "tx_type": self.tx_type.value,
            "action": self.action,
            "target_contract": self.target_contract,
            "function_name": self.function_name,
            "parameters": self.parameters,
            "value_wei": self.value_wei,
            "gas_estimate": self.gas_estimate,
            "evidence_refs": self.evidence_refs,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Transaction":
        """Create Transaction from dictionary."""
        tx_type = data.get("tx_type", "call")
        if isinstance(tx_type, str):
            tx_type = TransactionType(tx_type)

        return cls(
            order=int(data.get("order", 0)),
            tx_type=tx_type,
            action=str(data.get("action", "")),
            target_contract=str(data.get("target_contract", "")),
            function_name=str(data.get("function_name", "")),
            parameters=dict(data.get("parameters", {})),
            value_wei=int(data.get("value_wei", 0)),
            gas_estimate=int(data.get("gas_estimate", 100_000)),
            evidence_refs=list(data.get("evidence_refs", [])),
            metadata=dict(data.get("metadata", {})),
        )


@dataclass
class ExploitPath:
    """Complete exploit path with ordered transactions.

    Attributes:
        id: Unique path identifier
        transactions: Ordered list of transactions
        total_gas: Total gas required
        total_value_wei: Total ETH required
        description: Human-readable description
    """

    id: str
    transactions: List[Transaction] = field(default_factory=list)
    total_gas: int = 0
    total_value_wei: int = 0
    description: str = ""

    def __post_init__(self) -> None:
        """Calculate totals from transactions."""
        if self.transactions:
            self.total_gas = sum(tx.gas_estimate for tx in self.transactions)
            self.total_value_wei = sum(tx.value_wei for tx in self.transactions)

    def add_transaction(self, transaction: Transaction) -> None:
        """Add a transaction to the path."""
        self.transactions.append(transaction)
        self.total_gas += transaction.gas_estimate
        self.total_value_wei += transaction.value_wei

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "transactions": [tx.to_dict() for tx in self.transactions],
            "total_gas": self.total_gas,
            "total_value_wei": self.total_value_wei,
            "description": self.description,
        }


@dataclass
class AttackPlan:
    """A synthesized attack plan.

    Per 05.11-08: Contains exploit path, economic analysis, and MEV considerations.

    Attributes:
        id: Unique plan identifier
        vulnerability_id: ID of vulnerability being exploited
        exploit_path: Ordered transaction steps
        expected_profit: Expected profit in USD (from GATE)
        success_probability: Probability of successful execution
        required_capital: Capital required (flash loans, etc.)
        mev_vulnerability: Can this be frontrun?
        time_constraints: Timing windows and constraints
        causal_chain: References to CEG nodes in causal chain
        gate_matrix: Reference to GATE payoff matrix
        evidence_refs: Supporting evidence
        metadata: Additional metadata
    """

    id: str
    vulnerability_id: str
    exploit_path: ExploitPath
    expected_profit: Decimal = Decimal("0")
    success_probability: float = 0.5
    required_capital: Decimal = Decimal("0")
    mev_vulnerability: bool = False
    time_constraints: Dict[str, Any] = field(default_factory=dict)
    causal_chain: List[str] = field(default_factory=list)
    gate_matrix_id: str = ""
    evidence_refs: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_viable(self) -> bool:
        """Check if attack is economically viable (EV > 0)."""
        return float(self.expected_profit) > 0

    @property
    def expected_value(self) -> Decimal:
        """Calculate expected value (profit * probability)."""
        return self.expected_profit * Decimal(str(self.success_probability))

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "vulnerability_id": self.vulnerability_id,
            "exploit_path": self.exploit_path.to_dict(),
            "expected_profit": str(self.expected_profit),
            "success_probability": self.success_probability,
            "required_capital": str(self.required_capital),
            "mev_vulnerability": self.mev_vulnerability,
            "time_constraints": self.time_constraints,
            "causal_chain": self.causal_chain,
            "gate_matrix_id": self.gate_matrix_id,
            "evidence_refs": self.evidence_refs,
            "metadata": self.metadata,
        }


# =============================================================================
# MCTS Exploration Types
# =============================================================================


@dataclass
class MCTSConfig:
    """Configuration for MCTS exploration.

    Attributes:
        max_iterations: Maximum MCTS iterations
        max_depth: Maximum exploit path depth
        exploration_constant: UCB1 exploration parameter (c)
        min_ev_threshold: Minimum EV to continue exploration
        use_llm: Use LLM for move generation
        prune_negative_ev: Prune branches with EV < 0
    """

    max_iterations: int = 100
    max_depth: int = 10
    exploration_constant: float = 1.414  # sqrt(2)
    min_ev_threshold: float = 0.0
    use_llm: bool = False
    prune_negative_ev: bool = True


@dataclass
class ExplorationNode:
    """A node in the MCTS exploration tree.

    Represents a protocol state with available actions.

    Attributes:
        id: Unique node identifier
        state: Current protocol state representation
        available_actions: Actions that can be taken from this state
        visit_count: Number of times this node was visited
        total_value: Total accumulated value from simulations
        parent: Parent node (None for root)
        children: Child nodes
        is_terminal: Whether this is a terminal state
        depth: Depth in tree (0 for root)
    """

    id: str
    state: Dict[str, Any]
    available_actions: List[Transaction] = field(default_factory=list)
    visit_count: int = 0
    total_value: float = 0.0
    parent: Optional["ExplorationNode"] = None
    children: Dict[str, "ExplorationNode"] = field(default_factory=dict)
    is_terminal: bool = False
    depth: int = 0

    @property
    def mean_value(self) -> float:
        """Average value from simulations."""
        if self.visit_count == 0:
            return 0.0
        return self.total_value / self.visit_count

    def ucb1_score(self, exploration_constant: float = 1.414) -> float:
        """Calculate UCB1 score for node selection.

        UCB1 = mean_value + c * sqrt(ln(parent_visits) / visit_count)

        Args:
            exploration_constant: The exploration parameter (c)

        Returns:
            UCB1 score (higher = more promising)
        """
        if self.visit_count == 0:
            return float("inf")  # Unexplored nodes have infinite priority

        if self.parent is None or self.parent.visit_count == 0:
            return self.mean_value

        exploration_term = exploration_constant * math.sqrt(
            math.log(self.parent.visit_count) / self.visit_count
        )
        return self.mean_value + exploration_term

    def add_child(self, action: Transaction, state: Dict[str, Any]) -> "ExplorationNode":
        """Add a child node for a given action.

        Args:
            action: Transaction taken to reach child state
            state: Protocol state after action

        Returns:
            The new child node
        """
        child_id = f"{self.id}:{action.function_name or action.action}"
        child = ExplorationNode(
            id=child_id,
            state=state,
            parent=self,
            depth=self.depth + 1,
        )
        self.children[action.function_name or action.action] = child
        return child

    def backpropagate(self, value: float) -> None:
        """Backpropagate value up to root.

        Args:
            value: Value to backpropagate (e.g., attack EV)
        """
        node: Optional[ExplorationNode] = self
        while node is not None:
            node.visit_count += 1
            node.total_value += value
            node = node.parent


# =============================================================================
# Red Agent
# =============================================================================


class RedAgent:
    """Red Team agent for MCTS-style attack synthesis.

    Per 05.11-08: Synthesizes attacks using MCTS-inspired exploration with
    economic pruning via GATE. Generates viable attack plans with exploit paths.

    Key Features:
    - UCB1 selection for promising nodes
    - LLM-based move generation (available actions)
    - GATE integration for attack viability scoring
    - CEG integration for causal path structure
    - Economic pruning (EV < 0 branches)

    Usage:
        agent = RedAgent()
        plan = agent.synthesize_attack(
            finding={"id": "vuln-1", "severity": "high"},
            protocol_state={"tvl_usd": 10_000_000},
        )
    """

    def __init__(
        self,
        use_llm: bool = False,
        gate_engine: Optional[Any] = None,
        ceg_builder: Optional[Any] = None,
    ):
        """Initialize Red Agent.

        Args:
            use_llm: Enable LLM for move generation
            gate_engine: Optional GATE engine for economic analysis
            ceg_builder: Optional CEG builder for causal paths
        """
        self.use_llm = use_llm
        self.gate_engine = gate_engine
        self.ceg_builder = ceg_builder
        self._successful_attacks: List[AttackPlan] = []

    def synthesize_attack(
        self,
        finding: Dict[str, Any],
        protocol_state: Optional[Dict[str, Any]] = None,
        budget: Optional[MCTSConfig] = None,
    ) -> AttackPlan:
        """Synthesize attack plan using MCTS exploration.

        Per 05.11-08: Uses MCTS-style exploration with economic pruning.

        Args:
            finding: Vulnerability finding to exploit
            protocol_state: Current protocol state (TVL, gas price, etc.)
            budget: MCTS configuration (iterations, depth limits)

        Returns:
            AttackPlan with exploit path and economic analysis
        """
        protocol_state = protocol_state or {}
        budget = budget or MCTSConfig()

        vuln_id = finding.get("id", self._generate_id(finding))
        logger.info(f"RedAgent: Synthesizing attack for {vuln_id}")

        # Build initial exploration tree
        root = self._create_root_node(finding, protocol_state)

        # Run MCTS exploration
        best_path = self._mcts_explore(root, finding, protocol_state, budget)

        # Compute GATE economic analysis
        gate_result = self._compute_gate_analysis(finding, protocol_state, best_path)

        # Build causal chain from CEG
        causal_chain = self._build_causal_chain(finding, best_path)

        # Create attack plan
        plan = AttackPlan(
            id=f"attack:{vuln_id}:{self._generate_id(best_path.to_dict())}",
            vulnerability_id=vuln_id,
            exploit_path=best_path,
            expected_profit=Decimal(str(gate_result.get("expected_profit", 0))),
            success_probability=gate_result.get("success_probability", 0.5),
            required_capital=Decimal(str(gate_result.get("required_capital", 0))),
            mev_vulnerability=gate_result.get("mev_vulnerable", False),
            time_constraints=gate_result.get("time_constraints", {}),
            causal_chain=causal_chain,
            gate_matrix_id=gate_result.get("matrix_id", ""),
            evidence_refs=finding.get("evidence_refs", []),
            metadata={
                "mcts_iterations": budget.max_iterations,
                "tree_depth": root.depth,
                "severity": finding.get("severity", "unknown"),
            },
        )

        # Track successful attacks for improvement loop
        if plan.is_viable:
            self._successful_attacks.append(plan)

        logger.info(
            f"RedAgent: Synthesized {vuln_id}, "
            f"EV=${float(plan.expected_profit):,.2f}, "
            f"viable={plan.is_viable}"
        )

        return plan

    def _generate_id(self, data: Any) -> str:
        """Generate stable ID from data."""
        content = str(sorted(data.items()) if isinstance(data, dict) else data)
        return hashlib.sha256(content.encode()).hexdigest()[:8]

    def _create_root_node(
        self,
        finding: Dict[str, Any],
        protocol_state: Dict[str, Any],
    ) -> ExplorationNode:
        """Create root node for MCTS exploration.

        Args:
            finding: Vulnerability finding
            protocol_state: Current protocol state

        Returns:
            Root exploration node with initial available actions
        """
        vuln_id = finding.get("id", "unknown")
        initial_state = {
            "protocol": protocol_state.copy(),
            "attacker": {
                "balance": 0,
                "borrowed": 0,
            },
            "vulnerability": finding,
            "history": [],
        }

        root = ExplorationNode(
            id=f"root:{vuln_id}",
            state=initial_state,
        )

        # Generate initial available actions
        root.available_actions = self._generate_initial_actions(finding, protocol_state)

        return root

    def _generate_initial_actions(
        self,
        finding: Dict[str, Any],
        protocol_state: Dict[str, Any],
    ) -> List[Transaction]:
        """Generate initial available actions based on finding.

        Args:
            finding: Vulnerability finding
            protocol_state: Protocol state

        Returns:
            List of available transactions
        """
        actions: List[Transaction] = []
        pattern_id = finding.get("pattern_id", "").lower()
        severity = finding.get("severity", "medium").lower()

        # Flash loan option for high-value attacks
        tvl = protocol_state.get("tvl_usd", 0)
        if tvl > 100_000 and severity in ("critical", "high"):
            actions.append(
                Transaction(
                    order=1,
                    tx_type=TransactionType.FLASH_LOAN_BORROW,
                    action="Borrow flash loan to amplify capital",
                    function_name="flashLoan",
                    parameters={"amount": min(tvl * 0.1, 10_000_000)},
                )
            )

        # Direct exploit based on pattern
        if "reentrancy" in pattern_id:
            actions.append(
                Transaction(
                    order=1,
                    tx_type=TransactionType.CALL,
                    action="Call vulnerable function to initiate reentrancy",
                    function_name=finding.get("function_name", "withdraw"),
                )
            )
            actions.append(
                Transaction(
                    order=2,
                    tx_type=TransactionType.CALLBACK,
                    action="Reenter from malicious callback",
                    function_name="fallback",
                )
            )
        elif "access" in pattern_id or "auth" in pattern_id:
            actions.append(
                Transaction(
                    order=1,
                    tx_type=TransactionType.CALL,
                    action="Call unprotected privileged function",
                    function_name=finding.get("function_name", "setOwner"),
                )
            )
        elif "oracle" in pattern_id:
            actions.append(
                Transaction(
                    order=1,
                    tx_type=TransactionType.ORACLE_MANIPULATION,
                    action="Manipulate oracle price",
                    function_name="updatePrice",
                )
            )
            actions.append(
                Transaction(
                    order=2,
                    tx_type=TransactionType.CALL,
                    action="Exploit stale/manipulated price",
                    function_name=finding.get("function_name", "borrow"),
                )
            )
        elif "governance" in pattern_id:
            actions.append(
                Transaction(
                    order=1,
                    tx_type=TransactionType.GOVERNANCE,
                    action="Submit malicious governance proposal",
                    function_name="propose",
                )
            )
        else:
            # Default: direct call to vulnerable function
            actions.append(
                Transaction(
                    order=1,
                    tx_type=TransactionType.CALL,
                    action="Call vulnerable function",
                    function_name=finding.get("function_name", "unknown"),
                )
            )

        # Withdrawal/profit extraction always available
        actions.append(
            Transaction(
                order=len(actions) + 1,
                tx_type=TransactionType.WITHDRAW,
                action="Extract profits",
                function_name="withdraw",
            )
        )

        return actions

    def _mcts_explore(
        self,
        root: ExplorationNode,
        finding: Dict[str, Any],
        protocol_state: Dict[str, Any],
        config: MCTSConfig,
    ) -> ExploitPath:
        """Run MCTS exploration to find best exploit path.

        Args:
            root: Root exploration node
            finding: Vulnerability finding
            protocol_state: Protocol state
            config: MCTS configuration

        Returns:
            Best exploit path found
        """
        for iteration in range(config.max_iterations):
            # Selection: UCB1 to find promising node
            node = self._select_node(root, config.exploration_constant)

            # Expansion: Add child node if not terminal
            if not node.is_terminal and node.depth < config.max_depth:
                if node.available_actions:
                    action = random.choice(node.available_actions)
                    new_state = self._simulate_action(node.state, action)
                    child = node.add_child(action, new_state)

                    # Generate actions for child
                    child.available_actions = self._generate_next_actions(
                        child.state, finding, config
                    )

                    # Check if terminal
                    child.is_terminal = self._is_terminal_state(child.state, child.depth, config)

                    node = child

            # Simulation: Estimate value of this path
            value = self._simulate_outcome(node.state, finding, protocol_state, config)

            # Economic pruning: Skip negative EV branches
            if config.prune_negative_ev and value < config.min_ev_threshold:
                value = 0.0

            # Backpropagation: Update values up to root
            node.backpropagate(value)

        # Extract best path from tree
        return self._extract_best_path(root, finding)

    def _select_node(
        self,
        root: ExplorationNode,
        exploration_constant: float,
    ) -> ExplorationNode:
        """Select most promising node using UCB1.

        Args:
            root: Root node to start from
            exploration_constant: UCB1 exploration parameter

        Returns:
            Selected node for expansion
        """
        node = root

        while node.children:
            # Select child with highest UCB1 score
            best_child = None
            best_score = float("-inf")

            for child in node.children.values():
                score = child.ucb1_score(exploration_constant)
                if score > best_score:
                    best_score = score
                    best_child = child

            if best_child is None:
                break

            node = best_child

        return node

    def _simulate_action(
        self,
        state: Dict[str, Any],
        action: Transaction,
    ) -> Dict[str, Any]:
        """Simulate effect of action on state.

        Args:
            state: Current state
            action: Action to simulate

        Returns:
            New state after action
        """
        new_state = {
            "protocol": state.get("protocol", {}).copy(),
            "attacker": state.get("attacker", {}).copy(),
            "vulnerability": state.get("vulnerability", {}),
            "history": list(state.get("history", [])),
        }

        new_state["history"].append(action.to_dict())

        # Simulate state changes based on action type
        if action.tx_type == TransactionType.FLASH_LOAN_BORROW:
            amount = action.parameters.get("amount", 0)
            new_state["attacker"]["borrowed"] = amount
            new_state["attacker"]["balance"] = new_state["attacker"].get("balance", 0) + amount

        elif action.tx_type == TransactionType.WITHDRAW:
            # Simulate profit extraction
            vuln = state.get("vulnerability", {})
            severity = vuln.get("severity", "medium").lower()
            tvl = state.get("protocol", {}).get("tvl_usd", 1_000_000)

            extraction_rates = {
                "critical": 0.10,
                "high": 0.05,
                "medium": 0.01,
                "low": 0.001,
            }
            rate = extraction_rates.get(severity, 0.01)
            profit = min(tvl * rate, 10_000_000)
            new_state["attacker"]["balance"] = new_state["attacker"].get("balance", 0) + profit

        return new_state

    def _generate_next_actions(
        self,
        state: Dict[str, Any],
        finding: Dict[str, Any],
        config: MCTSConfig,
    ) -> List[Transaction]:
        """Generate available actions from current state.

        Args:
            state: Current state
            finding: Vulnerability finding
            config: MCTS configuration

        Returns:
            List of available actions
        """
        history_len = len(state.get("history", []))
        actions: List[Transaction] = []

        # If borrowed flash loan, must repay eventually
        borrowed = state.get("attacker", {}).get("borrowed", 0)
        if borrowed > 0:
            actions.append(
                Transaction(
                    order=history_len + 1,
                    tx_type=TransactionType.FLASH_LOAN_REPAY,
                    action="Repay flash loan",
                    function_name="repay",
                    parameters={"amount": borrowed},
                )
            )

        # Add extraction option
        balance = state.get("attacker", {}).get("balance", 0)
        if balance > 0:
            actions.append(
                Transaction(
                    order=history_len + 1,
                    tx_type=TransactionType.WITHDRAW,
                    action="Extract remaining profits",
                    function_name="withdraw",
                )
            )

        # Additional attack steps based on pattern
        pattern_id = finding.get("pattern_id", "").lower()
        if "reentrancy" in pattern_id and history_len < 5:
            actions.append(
                Transaction(
                    order=history_len + 1,
                    tx_type=TransactionType.CALLBACK,
                    action="Continue reentrancy chain",
                    function_name="fallback",
                )
            )

        return actions

    def _is_terminal_state(
        self,
        state: Dict[str, Any],
        depth: int,
        config: MCTSConfig,
    ) -> bool:
        """Check if state is terminal.

        Args:
            state: Current state
            depth: Current depth
            config: MCTS configuration

        Returns:
            True if terminal state
        """
        # Depth limit reached
        if depth >= config.max_depth:
            return True

        # Flash loan must be repaid - if borrowed and history includes repay
        borrowed = state.get("attacker", {}).get("borrowed", 0)
        history = state.get("history", [])
        has_repaid = any(h.get("tx_type") == "flash_loan_repay" for h in history)

        if borrowed > 0 and has_repaid:
            return True

        # Profit extracted
        if any(h.get("tx_type") == "withdraw" for h in history):
            return True

        return False

    def _simulate_outcome(
        self,
        state: Dict[str, Any],
        finding: Dict[str, Any],
        protocol_state: Dict[str, Any],
        config: MCTSConfig,
    ) -> float:
        """Simulate attack outcome to estimate value.

        Args:
            state: Current state
            finding: Vulnerability finding
            protocol_state: Protocol state
            config: MCTS configuration

        Returns:
            Estimated value (profit) of this path
        """
        # Use GATE if available
        if self.gate_engine is not None:
            try:
                matrix = self.gate_engine.compute_attack_ev(
                    vulnerability=finding,
                    protocol_state=protocol_state,
                )
                return matrix.expected_value_usd
            except Exception as e:
                logger.debug(f"GATE analysis failed: {e}")

        # Fallback: Simple heuristic based on severity and TVL
        severity = finding.get("severity", "medium").lower()
        tvl = protocol_state.get("tvl_usd", 1_000_000)

        # Base extraction rate by severity
        rates = {
            "critical": 0.10,
            "high": 0.05,
            "medium": 0.01,
            "low": 0.001,
        }
        rate = rates.get(severity, 0.01)

        # Adjust for success probability
        success_prob = finding.get("success_probability", 0.5)

        # Estimate costs
        gas_price = protocol_state.get("gas_price_gwei", 50)
        eth_price = protocol_state.get("eth_price_usd", 2000)
        gas_units = sum(
            h.get("gas_estimate", 100_000)
            for h in state.get("history", [])
        )
        gas_cost = (gas_price * gas_units / 1e9) * eth_price

        # Flash loan fees
        borrowed = state.get("attacker", {}).get("borrowed", 0)
        flash_fee = borrowed * 0.0009  # 0.09% fee

        # Expected value
        gross_profit = min(tvl * rate, 10_000_000)
        net_profit = (gross_profit * success_prob) - gas_cost - flash_fee

        return max(0, net_profit)

    def _extract_best_path(
        self,
        root: ExplorationNode,
        finding: Dict[str, Any],
    ) -> ExploitPath:
        """Extract best exploit path from MCTS tree.

        Args:
            root: Root of explored tree
            finding: Vulnerability finding

        Returns:
            Best exploit path
        """
        # Traverse tree following highest mean value
        path_transactions: List[Transaction] = []
        node = root

        while node.children:
            best_child = None
            best_value = float("-inf")

            for action_name, child in node.children.items():
                if child.mean_value > best_value:
                    best_value = child.mean_value
                    best_child = child

            if best_child is None:
                break

            # Find the action that led to this child
            for action in node.available_actions:
                if action.function_name == action_name or action.action == action_name:
                    action.order = len(path_transactions) + 1
                    path_transactions.append(action)
                    break

            node = best_child

        # Create exploit path
        vuln_id = finding.get("id", "unknown")
        path = ExploitPath(
            id=f"path:{vuln_id}:{len(path_transactions)}",
            transactions=path_transactions,
            description=f"Exploit path for {finding.get('pattern_id', 'unknown')} vulnerability",
        )

        return path

    def _compute_gate_analysis(
        self,
        finding: Dict[str, Any],
        protocol_state: Dict[str, Any],
        path: ExploitPath,
    ) -> Dict[str, Any]:
        """Compute GATE economic analysis for attack.

        Args:
            finding: Vulnerability finding
            protocol_state: Protocol state
            path: Exploit path

        Returns:
            GATE analysis results
        """
        # Use GATE engine if available
        if self.gate_engine is not None:
            try:
                matrix = self.gate_engine.compute_attack_ev(
                    vulnerability=finding,
                    protocol_state=protocol_state,
                )
                return {
                    "expected_profit": matrix.expected_value_usd,
                    "success_probability": 0.5,  # From matrix dominant strategies
                    "required_capital": sum(
                        tx.value_wei / 1e18 * protocol_state.get("eth_price_usd", 2000)
                        for tx in path.transactions
                    ),
                    "mev_vulnerable": matrix.is_attack_dominant(),
                    "time_constraints": {},
                    "matrix_id": matrix.vulnerability_id,
                }
            except Exception as e:
                logger.debug(f"GATE analysis failed: {e}")

        # Fallback heuristic
        severity = finding.get("severity", "medium").lower()
        tvl = protocol_state.get("tvl_usd", 1_000_000)

        rates = {"critical": 0.10, "high": 0.05, "medium": 0.01, "low": 0.001}
        rate = rates.get(severity, 0.01)
        gross = min(tvl * rate, 10_000_000)

        # Check for flash loan usage
        has_flash = any(
            tx.tx_type == TransactionType.FLASH_LOAN_BORROW
            for tx in path.transactions
        )
        required = gross * 10 if has_flash else gross * 0.01

        return {
            "expected_profit": gross * 0.5,  # 50% success rate
            "success_probability": 0.5,
            "required_capital": required,
            "mev_vulnerable": has_flash,  # Flash loans are MEV targets
            "time_constraints": {},
            "matrix_id": "",
        }

    def _build_causal_chain(
        self,
        finding: Dict[str, Any],
        path: ExploitPath,
    ) -> List[str]:
        """Build causal chain references from CEG.

        Args:
            finding: Vulnerability finding
            path: Exploit path

        Returns:
            List of CEG node IDs in causal chain
        """
        # Use CEG builder if available
        if self.ceg_builder is not None:
            try:
                # Build CEG from finding
                ceg = self.ceg_builder(finding.get("id", ""), None)
                if hasattr(ceg, "get_all_paths"):
                    # Get first path from root to loss
                    for node_id in ceg.nodes:
                        if node_id.startswith("root:"):
                            for target_id in ceg.nodes:
                                if target_id.startswith("loss:"):
                                    paths = ceg.get_all_paths(node_id, target_id)
                                    if paths:
                                        return [n.id for n in paths[0].nodes]
            except Exception as e:
                logger.debug(f"CEG building failed: {e}")

        # Fallback: Build simple causal chain from path
        vuln_id = finding.get("id", "unknown")
        pattern_id = finding.get("pattern_id", "unknown")

        chain = [
            f"root:{pattern_id}",
        ]

        for tx in path.transactions:
            if tx.tx_type == TransactionType.CALLBACK:
                chain.append(f"step:callback_abuse")
            elif tx.tx_type == TransactionType.ORACLE_MANIPULATION:
                chain.append(f"step:price_manipulation")
            elif tx.tx_type == TransactionType.CALL:
                chain.append(f"step:exploit_{tx.function_name}")

        chain.append(f"loss:fund_extraction")

        return chain

    def get_successful_attacks(self) -> List[AttackPlan]:
        """Get list of successful attacks for improvement loop.

        Returns:
            List of attack plans with positive EV
        """
        return [a for a in self._successful_attacks if a.is_viable]

    def clear_attack_history(self) -> None:
        """Clear attack history for new simulation."""
        self._successful_attacks.clear()


# =============================================================================
# Module Exports
# =============================================================================


__all__ = [
    "RedAgent",
    "AttackPlan",
    "ExploitPath",
    "Transaction",
    "TransactionType",
    "ExplorationNode",
    "MCTSConfig",
]
