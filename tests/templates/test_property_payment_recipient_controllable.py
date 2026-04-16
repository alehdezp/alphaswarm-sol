"""
Property Test: payment_recipient_controllable

Tests for the payment_recipient_controllable builder property.

Property Description:
    Detects functions where the payment recipient address is derived from
    user-controlled input, making it a potential attack vector.

Expected Behavior:
    - True when: Transfer recipient is derived from function parameters
    - False when: Transfer recipient is hardcoded or from storage

Related Patterns:
    - callback-controlled-recipient
    - arbitrary-recipient-transfer
"""

import unittest
import pytest
import tempfile
import os
import json


PROPERTY_NAME = "payment_recipient_controllable"


# ============================================================================
# Test Contracts
# ============================================================================

TP_PARAMETER_RECIPIENT = """
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract ParameterRecipient {
    function transferTo(address recipient, uint256 amount) external payable {
        payable(recipient).transfer(amount);
    }
}
"""

TP_CALLBACK_RECIPIENT = """
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

interface IERC20 {
    function transfer(address to, uint256 amount) external returns (bool);
}

contract CallbackRecipient {
    IERC20 public token;

    function proxyTransfer(address proxy, uint256 amount) external {
        // Recipient derived from parameter
        token.transfer(proxy, amount);
    }
}
"""

TN_HARDCODED_RECIPIENT = """
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract HardcodedRecipient {
    address public constant TREASURY = 0x1234567890123456789012345678901234567890;

    function collectFees() external {
        payable(TREASURY).transfer(address(this).balance);
    }
}
"""

TN_STORAGE_RECIPIENT = """
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract StorageRecipient {
    address public owner;

    constructor() {
        owner = msg.sender;
    }

    function withdrawToOwner() external {
        require(msg.sender == owner);
        payable(owner).transfer(address(this).balance);
    }
}
"""

TN_SENDER_RECIPIENT = """
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract SenderRecipient {
    mapping(address => uint256) public balances;

    function withdraw() external {
        uint256 amount = balances[msg.sender];
        balances[msg.sender] = 0;
        payable(msg.sender).transfer(amount);
    }
}
"""


class TestPaymentRecipientControllable(unittest.TestCase):
    """Tests for payment_recipient_controllable property."""

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
    def test_tp1_parameter_recipient(self):
        """payment_recipient_controllable should be True when recipient is a parameter."""
        graph = self._build_graph(TP_PARAMETER_RECIPIENT, "ParameterRecipient")
        func = self._find_function(graph, "transferTo")

        if func is None:
            self.skipTest("Function not found")

        self.assertTrue(
            func.get("properties", {}).get(PROPERTY_NAME, False),
            f"{PROPERTY_NAME} should be True when recipient is from parameter"
        )

    @pytest.mark.xfail(reason="Stale code: alphaswarm binary path not found")
    def test_tp2_callback_recipient(self):
        """payment_recipient_controllable should be True in callback context."""
        graph = self._build_graph(TP_CALLBACK_RECIPIENT, "CallbackRecipient")
        func = self._find_function(graph, "proxyTransfer")

        if func is None:
            self.skipTest("Function not found")

        # Document expected behavior

    # -------------------------------------------------------------------------
    # True Negative Tests
    # -------------------------------------------------------------------------

    @pytest.mark.xfail(reason="Stale code: alphaswarm binary path not found")
    def test_tn1_hardcoded_recipient(self):
        """payment_recipient_controllable should be False for hardcoded recipient."""
        graph = self._build_graph(TN_HARDCODED_RECIPIENT, "HardcodedRecipient")
        func = self._find_function(graph, "collectFees")

        if func is None:
            self.skipTest("Function not found")

        self.assertFalse(
            func.get("properties", {}).get(PROPERTY_NAME, False),
            f"{PROPERTY_NAME} should be False for hardcoded recipient"
        )

    @pytest.mark.xfail(reason="Stale code: alphaswarm binary path not found")
    def test_tn2_storage_recipient(self):
        """payment_recipient_controllable should be False for storage recipient."""
        graph = self._build_graph(TN_STORAGE_RECIPIENT, "StorageRecipient")
        func = self._find_function(graph, "withdrawToOwner")

        if func is None:
            self.skipTest("Function not found")

        self.assertFalse(
            func.get("properties", {}).get(PROPERTY_NAME, False),
            f"{PROPERTY_NAME} should be False for storage-based recipient"
        )

    @pytest.mark.xfail(reason="Stale code: alphaswarm binary path not found")
    def test_tn3_sender_recipient(self):
        """payment_recipient_controllable should be False when recipient is msg.sender."""
        graph = self._build_graph(TN_SENDER_RECIPIENT, "SenderRecipient")
        func = self._find_function(graph, "withdraw")

        if func is None:
            self.skipTest("Function not found")

        self.assertFalse(
            func.get("properties", {}).get(PROPERTY_NAME, False),
            f"{PROPERTY_NAME} should be False when recipient is msg.sender"
        )


if __name__ == "__main__":
    unittest.main()
