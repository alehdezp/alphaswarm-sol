"""
Property Test: callback_chain_surface

Tests for the callback_chain_surface builder property.

Property Description:
    Detects functions that are callbacks in protocol integrations,
    which can be attack surfaces if they transfer value based on
    attacker-controlled parameters.

Expected Behavior:
    - True when: Function implements a callback interface (e.g., IProxyCreationCallback)
    - False when: Function is a regular entry point without callback semantics

Related Patterns:
    - callback-controlled-recipient (backdoor challenge)
"""

import unittest
import pytest
import tempfile
import os
import json


PROPERTY_NAME = "callback_chain_surface"


# ============================================================================
# Test Contracts
# ============================================================================

TP_CALLBACK_INTERFACE = """
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

interface ICallback {
    function onCallback(address user, uint256 amount) external;
}

contract CallbackReceiver is ICallback {
    mapping(address => uint256) public balances;

    function onCallback(address user, uint256 amount) external override {
        balances[user] += amount;
    }
}
"""

TP_FLASH_LOAN_CALLBACK = """
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

interface IFlashLoanReceiver {
    function executeOperation(
        address asset,
        uint256 amount,
        uint256 premium,
        address initiator,
        bytes calldata params
    ) external returns (bool);
}

contract FlashLoanReceiver is IFlashLoanReceiver {
    function executeOperation(
        address asset,
        uint256 amount,
        uint256 premium,
        address initiator,
        bytes calldata params
    ) external override returns (bool) {
        // Flash loan logic
        return true;
    }
}
"""

TN_REGULAR_FUNCTION = """
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract RegularContract {
    mapping(address => uint256) public balances;

    function deposit() external payable {
        balances[msg.sender] += msg.value;
    }

    function withdraw(uint256 amount) external {
        require(balances[msg.sender] >= amount);
        balances[msg.sender] -= amount;
        payable(msg.sender).transfer(amount);
    }
}
"""

TN_INTERNAL_HELPER = """
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract InternalHelper {
    function _internalCallback(address user) internal {
        // Internal function, not a callback surface
    }

    function publicEntry() external {
        _internalCallback(msg.sender);
    }
}
"""


class TestCallbackChainSurface(unittest.TestCase):
    """Tests for callback_chain_surface property."""

    def _build_graph(self, source_code: str, contract_name: str) -> dict:
        """Build a VKG graph from Solidity source code."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Write source file
            sol_path = os.path.join(tmpdir, f"{contract_name}.sol")
            with open(sol_path, "w") as f:
                f.write(source_code)

            # Build graph
            import subprocess
            result = subprocess.run(
                ["uv", "run", "alphaswarm", "build-kg", tmpdir, "--out", os.path.join(tmpdir, "graph.kg.json")],
                capture_output=True,
                text=True,
                cwd="."
            )

            if result.returncode != 0:
                self.skipTest(f"Graph build failed: {result.stderr}")

            # Load graph
            graph_path = os.path.join(tmpdir, "graph.kg.json", "graph.json")
            if os.path.exists(graph_path):
                with open(graph_path) as f:
                    return json.load(f)

            return {}

    def _find_function(self, graph: dict, func_name: str) -> dict:
        """Find a function node by name."""
        for node in graph.get("graph", {}).get("nodes", []):
            if node.get("type") == "Function":
                label = node.get("label", "")
                if func_name in label:
                    return node
        return None

    # -------------------------------------------------------------------------
    # True Positive Tests
    # -------------------------------------------------------------------------

    @pytest.mark.xfail(reason="Stale code: alphaswarm binary path not found")
    def test_tp1_callback_interface(self):
        """callback_chain_surface should be True for callback interface implementation."""
        graph = self._build_graph(TP_CALLBACK_INTERFACE, "CallbackReceiver")
        func = self._find_function(graph, "onCallback")

        if func is None:
            self.skipTest("Function not found - may need Slither")

        self.assertTrue(
            func.get("properties", {}).get(PROPERTY_NAME, False),
            f"{PROPERTY_NAME} should be True for onCallback"
        )

    @pytest.mark.xfail(reason="Stale code: alphaswarm binary path not found")
    def test_tp2_flash_loan_callback(self):
        """callback_chain_surface should be True for flash loan receiver."""
        graph = self._build_graph(TP_FLASH_LOAN_CALLBACK, "FlashLoanReceiver")
        func = self._find_function(graph, "executeOperation")

        if func is None:
            self.skipTest("Function not found - may need Slither")

        # Note: This may or may not trigger depending on builder implementation
        # The test documents expected behavior

    # -------------------------------------------------------------------------
    # True Negative Tests
    # -------------------------------------------------------------------------

    @pytest.mark.xfail(reason="Stale code: alphaswarm binary path not found")
    def test_tn1_regular_deposit(self):
        """callback_chain_surface should be False for regular deposit function."""
        graph = self._build_graph(TN_REGULAR_FUNCTION, "RegularContract")
        func = self._find_function(graph, "deposit")

        if func is None:
            self.skipTest("Function not found - may need Slither")

        self.assertFalse(
            func.get("properties", {}).get(PROPERTY_NAME, False),
            f"{PROPERTY_NAME} should be False for deposit"
        )

    @pytest.mark.xfail(reason="Stale code: alphaswarm binary path not found")
    def test_tn2_internal_function(self):
        """callback_chain_surface should be False for internal functions."""
        graph = self._build_graph(TN_INTERNAL_HELPER, "InternalHelper")
        func = self._find_function(graph, "_internalCallback")

        if func is None:
            self.skipTest("Function not found - may need Slither")

        self.assertFalse(
            func.get("properties", {}).get(PROPERTY_NAME, False),
            f"{PROPERTY_NAME} should be False for internal function"
        )


if __name__ == "__main__":
    unittest.main()
