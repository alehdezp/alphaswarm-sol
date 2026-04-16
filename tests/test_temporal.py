"""Phase 16: Temporal Execution Layer Tests.

Tests for state transition tracking and vulnerability window detection.
"""

import unittest
from typing import Any, Dict, List

from alphaswarm_sol.kg.schema import KnowledgeGraph, Node, Edge
from alphaswarm_sol.kg.temporal import (
    StateType,
    VulnerabilityWindow,
    StateTransition,
    AttackWindow,
    StateMachine,
    StateMachineBuilder,
    build_state_machine,
    detect_temporal_vulnerabilities,
    get_dangerous_transitions,
)


class TestStateType(unittest.TestCase):
    """Tests for StateType enum."""

    def test_state_types_defined(self):
        """All state types are defined."""
        self.assertEqual(StateType.UNINITIALIZED.value, "uninitialized")
        self.assertEqual(StateType.INITIALIZED.value, "initialized")
        self.assertEqual(StateType.ACTIVE.value, "active")
        self.assertEqual(StateType.PAUSED.value, "paused")
        self.assertEqual(StateType.LOCKED.value, "locked")


class TestVulnerabilityWindow(unittest.TestCase):
    """Tests for VulnerabilityWindow enum."""

    def test_window_types_defined(self):
        """All window types are defined."""
        self.assertEqual(VulnerabilityWindow.FLASH_LOAN.value, "flash_loan")
        self.assertEqual(VulnerabilityWindow.INITIALIZATION.value, "initialization")
        self.assertEqual(VulnerabilityWindow.GOVERNANCE.value, "governance")


class TestStateTransition(unittest.TestCase):
    """Tests for StateTransition dataclass."""

    def test_transition_creation(self):
        """StateTransition can be created with all fields."""
        trans = StateTransition(
            id="trans_1",
            from_state={"paused": False},
            to_state={"paused": True},
            trigger_function="pause",
            guard_conditions=["onlyOwner"],
            enables_attacks=[],
            state_vars_modified=["paused"],
        )

        self.assertEqual(trans.id, "trans_1")
        self.assertEqual(trans.trigger_function, "pause")
        self.assertEqual(trans.from_state["paused"], False)
        self.assertEqual(trans.to_state["paused"], True)

    def test_to_dict(self):
        """StateTransition serializes correctly."""
        trans = StateTransition(
            id="trans_1",
            from_state={"active": True},
            to_state={"active": False},
            trigger_function="deactivate",
        )

        d = trans.to_dict()
        self.assertEqual(d["id"], "trans_1")
        self.assertEqual(d["trigger_function"], "deactivate")

    def test_from_dict(self):
        """StateTransition deserializes correctly."""
        d = {
            "id": "trans_1",
            "from_state": {"locked": False},
            "to_state": {"locked": True},
            "trigger_function": "lock",
            "guard_conditions": ["access_control"],
            "enables_attacks": ["dos"],
        }

        trans = StateTransition.from_dict(d)
        self.assertEqual(trans.id, "trans_1")
        self.assertEqual(trans.trigger_function, "lock")
        self.assertIn("dos", trans.enables_attacks)


class TestAttackWindow(unittest.TestCase):
    """Tests for AttackWindow dataclass."""

    def test_window_creation(self):
        """AttackWindow can be created with all fields."""
        window = AttackWindow(
            id="window_1",
            window_type=VulnerabilityWindow.FLASH_LOAN,
            start_trigger="swap",
            end_trigger="same transaction",
            duration="1 tx",
            enabled_attacks=["price_manipulation"],
            risk_level=8,
            mitigations=["Use TWAP"],
        )

        self.assertEqual(window.id, "window_1")
        self.assertEqual(window.window_type, VulnerabilityWindow.FLASH_LOAN)
        self.assertEqual(window.risk_level, 8)

    def test_to_dict(self):
        """AttackWindow serializes correctly."""
        window = AttackWindow(
            id="window_1",
            window_type=VulnerabilityWindow.INITIALIZATION,
            start_trigger="deployment",
            enabled_attacks=["unprotected_init"],
        )

        d = window.to_dict()
        self.assertEqual(d["window_type"], "initialization")
        self.assertIn("unprotected_init", d["enabled_attacks"])


class TestStateMachine(unittest.TestCase):
    """Tests for StateMachine dataclass."""

    def test_state_machine_creation(self):
        """StateMachine can be created with all fields."""
        sm = StateMachine(
            contract_id="test_contract",
            states=["active", "paused"],
            transitions=[
                StateTransition(id="t1", trigger_function="pause"),
            ],
            initial_state="active",
        )

        self.assertEqual(sm.contract_id, "test_contract")
        self.assertEqual(sm.state_count, 2)
        self.assertEqual(sm.transition_count, 1)
        self.assertEqual(sm.initial_state, "active")

    def test_get_dangerous_transitions(self):
        """get_dangerous_transitions returns correct transitions."""
        sm = StateMachine(
            contract_id="test",
            states=["active"],
            transitions=[
                StateTransition(id="t1", trigger_function="safe", enables_attacks=[]),
                StateTransition(id="t2", trigger_function="dangerous", enables_attacks=["reentrancy"]),
            ],
        )

        dangerous = sm.get_dangerous_transitions()
        self.assertEqual(len(dangerous), 1)
        self.assertEqual(dangerous[0].trigger_function, "dangerous")

    def test_to_dict(self):
        """StateMachine serializes correctly."""
        sm = StateMachine(
            contract_id="test",
            states=["active", "paused"],
            initial_state="active",
        )

        d = sm.to_dict()
        self.assertEqual(d["contract_id"], "test")
        self.assertEqual(d["state_count"], 2)
        self.assertEqual(d["initial_state"], "active")


class TestStateMachineBuilder(unittest.TestCase):
    """Tests for StateMachineBuilder class."""

    def test_build_basic_state_machine(self):
        """Builder creates state machine from graph."""
        graph = KnowledgeGraph(
            nodes={
                "contract1": Node(
                    id="contract1",
                    label="Pausable",
                    type="Contract",
                ),
                "paused_var": Node(
                    id="paused_var",
                    label="paused",
                    type="StateVariable",
                    properties={"is_boolean": True},
                ),
                "pause_func": Node(
                    id="pause_func",
                    label="pause",
                    type="Function",
                    properties={
                        "contract_name": "Pausable",
                        "writes_state": True,
                        "has_access_gate": True,
                    }
                ),
            },
            edges={},
            metadata={},
        )

        builder = StateMachineBuilder(graph)
        sm = builder.build("contract1")

        self.assertEqual(sm.contract_id, "contract1")
        self.assertIn("paused", sm.states)
        self.assertIn("active", sm.states)

    def test_detect_initialization_transition(self):
        """Builder detects initialization transitions."""
        graph = KnowledgeGraph(
            nodes={
                "contract1": Node(
                    id="contract1",
                    label="Initializable",
                    type="Contract",
                ),
                "init_var": Node(
                    id="init_var",
                    label="initialized",
                    type="StateVariable",
                    properties={"is_boolean": True},
                ),
                "init_func": Node(
                    id="init_func",
                    label="initialize",
                    type="Function",
                    properties={
                        "contract_name": "Initializable",
                        "writes_state": True,
                        "is_initializer_like": True,
                    }
                ),
            },
            edges={},
            metadata={},
        )

        builder = StateMachineBuilder(graph)
        sm = builder.build("contract1")

        self.assertIn("initialized", sm.states)
        self.assertIn("uninitialized", sm.states)

        # Check for initialization transition
        init_trans = [t for t in sm.transitions if "initialized" in t.state_vars_modified]
        self.assertEqual(len(init_trans), 1)

    def test_detect_reentrancy_vulnerability(self):
        """Builder detects reentrancy vulnerability windows."""
        graph = KnowledgeGraph(
            nodes={
                "contract1": Node(
                    id="contract1",
                    label="Vulnerable",
                    type="Contract",
                ),
                "withdraw_func": Node(
                    id="withdraw_func",
                    label="withdraw",
                    type="Function",
                    properties={
                        "contract_name": "Vulnerable",
                        "writes_state": True,
                        "state_write_after_external_call": True,
                        "has_reentrancy_guard": False,
                    }
                ),
            },
            edges={},
            metadata={},
        )

        builder = StateMachineBuilder(graph)
        sm = builder.build("contract1")

        # Check for reentrancy attack window
        dangerous = sm.get_dangerous_transitions()
        self.assertEqual(len(dangerous), 1)
        self.assertIn("reentrancy", dangerous[0].enables_attacks)

        # Check for attack window
        reentrant_windows = [
            w for w in sm.attack_windows
            if "reentrancy" in w.enabled_attacks
        ]
        self.assertGreater(len(reentrant_windows), 0)

    def test_detect_flash_loan_window(self):
        """Builder detects flash loan vulnerability windows."""
        graph = KnowledgeGraph(
            nodes={
                "contract1": Node(
                    id="contract1",
                    label="PriceDependent",
                    type="Contract",
                ),
                "price_func": Node(
                    id="price_func",
                    label="getPrice",
                    type="Function",
                    properties={
                        "contract_name": "PriceDependent",
                        "reads_oracle_price": True,
                        "has_staleness_check": False,
                    }
                ),
            },
            edges={},
            metadata={},
        )

        builder = StateMachineBuilder(graph)
        sm = builder.build("contract1")

        # Check for flash loan attack window
        flash_windows = [
            w for w in sm.attack_windows
            if w.window_type == VulnerabilityWindow.FLASH_LOAN
        ]
        self.assertGreater(len(flash_windows), 0)

    def test_detect_unauthorized_access(self):
        """Builder detects unauthorized access vulnerabilities."""
        graph = KnowledgeGraph(
            nodes={
                "contract1": Node(
                    id="contract1",
                    label="Ownable",
                    type="Contract",
                ),
                "owner_func": Node(
                    id="owner_func",
                    label="setOwner",
                    type="Function",
                    properties={
                        "contract_name": "Ownable",
                        "writes_state": True,
                        "writes_privileged_state": True,
                        "has_access_gate": False,
                        "semantic_ops": ["MODIFIES_OWNER"],
                    }
                ),
            },
            edges={},
            metadata={},
        )

        builder = StateMachineBuilder(graph)
        sm = builder.build("contract1")

        dangerous = sm.get_dangerous_transitions()
        self.assertEqual(len(dangerous), 1)
        self.assertIn("unauthorized_access", dangerous[0].enables_attacks)

    def test_initialization_window(self):
        """Builder detects initialization attack window."""
        graph = KnowledgeGraph(
            nodes={
                "contract1": Node(
                    id="contract1",
                    label="Proxy",
                    type="Contract",
                ),
                "init_func": Node(
                    id="init_func",
                    label="initialize",
                    type="Function",
                    properties={
                        "contract_name": "Proxy",
                        "writes_state": True,
                        "is_initializer_like": True,
                    }
                ),
            },
            edges={},
            metadata={},
        )

        builder = StateMachineBuilder(graph)
        sm = builder.build("contract1")

        init_windows = [
            w for w in sm.attack_windows
            if w.window_type == VulnerabilityWindow.INITIALIZATION
        ]
        self.assertGreater(len(init_windows), 0)


class TestConvenienceFunctions(unittest.TestCase):
    """Tests for convenience functions."""

    def test_build_state_machine(self):
        """build_state_machine convenience function works."""
        graph = KnowledgeGraph(
            nodes={
                "contract1": Node(
                    id="contract1",
                    label="Test",
                    type="Contract",
                ),
            },
            edges={},
            metadata={},
        )

        sm = build_state_machine(graph, "contract1")
        self.assertEqual(sm.contract_id, "contract1")

    def test_detect_temporal_vulnerabilities(self):
        """detect_temporal_vulnerabilities returns windows."""
        sm = StateMachine(
            contract_id="test",
            attack_windows=[
                AttackWindow(
                    id="w1",
                    window_type=VulnerabilityWindow.FLASH_LOAN,
                )
            ]
        )

        windows = detect_temporal_vulnerabilities(sm)
        self.assertEqual(len(windows), 1)

    def test_get_dangerous_transitions_func(self):
        """get_dangerous_transitions convenience function works."""
        sm = StateMachine(
            contract_id="test",
            transitions=[
                StateTransition(id="t1", enables_attacks=["reentrancy"]),
            ]
        )

        dangerous = get_dangerous_transitions(sm)
        self.assertEqual(len(dangerous), 1)


class TestComplexScenarios(unittest.TestCase):
    """Tests for complex multi-state scenarios."""

    def test_multiple_state_variables(self):
        """Builder handles contracts with multiple state variables."""
        graph = KnowledgeGraph(
            nodes={
                "contract1": Node(
                    id="contract1",
                    label="Complex",
                    type="Contract",
                ),
                "paused_var": Node(
                    id="paused_var",
                    label="paused",
                    type="StateVariable",
                    properties={"is_boolean": True},
                ),
                "locked_var": Node(
                    id="locked_var",
                    label="locked",
                    type="StateVariable",
                    properties={"is_boolean": True},
                ),
                "initialized_var": Node(
                    id="initialized_var",
                    label="initialized",
                    type="StateVariable",
                    properties={"is_boolean": True},
                ),
            },
            edges={},
            metadata={},
        )

        builder = StateMachineBuilder(graph)
        sm = builder.build("contract1")

        # Should have states for all state variables
        self.assertIn("paused", sm.states)
        self.assertIn("active", sm.states)
        self.assertIn("locked", sm.states)
        self.assertIn("unlocked", sm.states)
        self.assertIn("initialized", sm.states)
        self.assertIn("uninitialized", sm.states)

    def test_initial_state_detection(self):
        """Builder correctly determines initial state."""
        graph = KnowledgeGraph(
            nodes={
                "contract1": Node(
                    id="contract1",
                    label="Initializable",
                    type="Contract",
                ),
                "init_var": Node(
                    id="init_var",
                    label="initialized",
                    type="StateVariable",
                    properties={"is_boolean": True},
                ),
            },
            edges={},
            metadata={},
        )

        builder = StateMachineBuilder(graph)
        sm = builder.build("contract1")

        # Should prefer uninitialized as initial state
        self.assertEqual(sm.initial_state, "uninitialized")


if __name__ == "__main__":
    unittest.main()
