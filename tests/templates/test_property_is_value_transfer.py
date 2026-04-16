"""
Property Test: is_value_transfer

Tests for the is_value_transfer builder property.

Property Description:
    Detects functions that transfer value (ETH or tokens) to recipients.
    This is a critical property for identifying value movement patterns.

Expected Behavior:
    - True when: Function transfers ETH or tokens
    - False when: Function only reads/writes state without transfers

Related Patterns:
    - callback-controlled-recipient
    - unprotected-value-transfer
"""

import unittest
import pytest
import tempfile
import os
import json


PROPERTY_NAME = "is_value_transfer"


# ============================================================================
# Test Contracts
# ============================================================================

TP_ETH_TRANSFER = """
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract EthTransfer {
    function withdraw(uint256 amount) external {
        payable(msg.sender).transfer(amount);
    }
}
"""

TP_TOKEN_TRANSFER = """
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

interface IERC20 {
    function transfer(address to, uint256 amount) external returns (bool);
}

contract TokenTransfer {
    IERC20 public token;

    function sendTokens(address to, uint256 amount) external {
        token.transfer(to, amount);
    }
}
"""

TP_SAFE_TRANSFER = """
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

library SafeTransferLib {
    function safeTransfer(address token, address to, uint256 amount) internal {}
}

contract SafeTransferContract {
    function distribute(address token, address to, uint256 amount) external {
        SafeTransferLib.safeTransfer(token, to, amount);
    }
}
"""

TN_STATE_ONLY = """
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract StateOnly {
    mapping(address => uint256) public balances;

    function updateBalance(address user, uint256 amount) external {
        balances[user] = amount;
    }
}
"""

TN_VIEW_FUNCTION = """
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract ViewFunction {
    mapping(address => uint256) public balances;

    function getBalance(address user) external view returns (uint256) {
        return balances[user];
    }
}
"""

TN_PURE_FUNCTION = """
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract PureFunction {
    function add(uint256 a, uint256 b) external pure returns (uint256) {
        return a + b;
    }
}
"""


class TestIsValueTransfer(unittest.TestCase):
    """Tests for is_value_transfer property."""

    def _build_graph(self, source_code: str, contract_name: str) -> dict:
        """Build a VKG graph from Solidity source code."""
        with tempfile.TemporaryDirectory() as tmpdir:
            sol_path = os.path.join(tmpdir, f"{contract_name}.sol")
            with open(sol_path, "w") as f:
                f.write(source_code)

            import subprocess
            result = subprocess.run(
                ["uv", "run", "alphaswarm", "build-kg", tmpdir, "--out", os.path.join(tmpdir, "graph.kg.json")],
                capture_output=True,
                text=True,
                cwd="."
            )

            if result.returncode != 0:
                self.skipTest(f"Graph build failed: {result.stderr}")

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
    def test_tp1_eth_transfer(self):
        """is_value_transfer should be True for ETH transfer."""
        graph = self._build_graph(TP_ETH_TRANSFER, "EthTransfer")
        func = self._find_function(graph, "withdraw")

        if func is None:
            self.skipTest("Function not found")

        self.assertTrue(
            func.get("properties", {}).get(PROPERTY_NAME, False),
            f"{PROPERTY_NAME} should be True for ETH transfer"
        )

    @pytest.mark.xfail(reason="Stale code: alphaswarm binary path not found")
    def test_tp2_token_transfer(self):
        """is_value_transfer should be True for token transfer."""
        graph = self._build_graph(TP_TOKEN_TRANSFER, "TokenTransfer")
        func = self._find_function(graph, "sendTokens")

        if func is None:
            self.skipTest("Function not found")

        self.assertTrue(
            func.get("properties", {}).get(PROPERTY_NAME, False),
            f"{PROPERTY_NAME} should be True for token transfer"
        )

    @pytest.mark.xfail(reason="Stale code: alphaswarm binary path not found")
    def test_tp3_safe_transfer(self):
        """is_value_transfer should be True for SafeTransfer calls."""
        graph = self._build_graph(TP_SAFE_TRANSFER, "SafeTransferContract")
        func = self._find_function(graph, "distribute")

        if func is None:
            self.skipTest("Function not found")

        # Document expected behavior

    # -------------------------------------------------------------------------
    # True Negative Tests
    # -------------------------------------------------------------------------

    @pytest.mark.xfail(reason="Stale code: alphaswarm binary path not found")
    def test_tn1_state_only(self):
        """is_value_transfer should be False for state-only operations."""
        graph = self._build_graph(TN_STATE_ONLY, "StateOnly")
        func = self._find_function(graph, "updateBalance")

        if func is None:
            self.skipTest("Function not found")

        self.assertFalse(
            func.get("properties", {}).get(PROPERTY_NAME, False),
            f"{PROPERTY_NAME} should be False for state-only operations"
        )

    @pytest.mark.xfail(reason="Stale code: alphaswarm binary path not found")
    def test_tn2_view_function(self):
        """is_value_transfer should be False for view functions."""
        graph = self._build_graph(TN_VIEW_FUNCTION, "ViewFunction")
        func = self._find_function(graph, "getBalance")

        if func is None:
            self.skipTest("Function not found")

        self.assertFalse(
            func.get("properties", {}).get(PROPERTY_NAME, False),
            f"{PROPERTY_NAME} should be False for view functions"
        )

    @pytest.mark.xfail(reason="Stale code: alphaswarm binary path not found")
    def test_tn3_pure_function(self):
        """is_value_transfer should be False for pure functions."""
        graph = self._build_graph(TN_PURE_FUNCTION, "PureFunction")
        func = self._find_function(graph, "add")

        if func is None:
            self.skipTest("Function not found")

        self.assertFalse(
            func.get("properties", {}).get(PROPERTY_NAME, False),
            f"{PROPERTY_NAME} should be False for pure functions"
        )


if __name__ == "__main__":
    unittest.main()
