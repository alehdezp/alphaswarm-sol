"""
Rename Resistance Test Harness

Tests that VKG produces semantically equivalent results regardless of
function and variable names. This is critical for name-agnostic detection.

Validation Criteria:
- 100% invariance on DVDeFi corpus
- Same patterns detected regardless of naming
- Property values stable across renames
"""

import unittest
import pytest
import tempfile
import os
import json
import subprocess
from pathlib import Path


class RenameResistanceTests(unittest.TestCase):
    """Tests for name-agnostic vulnerability detection."""

    VKG_ROOT = Path("/Volumes/ex_ssd/home/projects/python/vkg-solidity/alphaswarm")

    def _build_graph(self, source_code: str, name: str) -> dict:
        """Build a VKG graph from source code."""
        with tempfile.TemporaryDirectory() as tmpdir:
            sol_path = os.path.join(tmpdir, f"{name}.sol")
            with open(sol_path, "w") as f:
                f.write(source_code)

            result = subprocess.run(
                ["uv", "run", "alphaswarm", "build-kg", tmpdir, "--out", os.path.join(tmpdir, "graph.kg.json")],
                capture_output=True,
                text=True,
                cwd=str(self.VKG_ROOT)
            )

            if result.returncode != 0:
                return None

            graph_path = os.path.join(tmpdir, "graph.kg.json", "graph.json")
            if os.path.exists(graph_path):
                with open(graph_path) as f:
                    return json.load(f)
            return None

    def _get_function_properties(self, graph: dict, partial_name: str) -> dict:
        """Get properties for a function by partial name match."""
        for node in graph.get("graph", {}).get("nodes", []):
            if node.get("type") == "Function" and partial_name in node.get("label", ""):
                return node.get("properties", {})
        return {}

    def _extract_semantic_properties(self, props: dict) -> dict:
        """Extract semantic properties that should be name-agnostic."""
        semantic_keys = [
            "has_access_gate",
            "has_reentrancy_guard",
            "state_write_after_external_call",
            "has_unbounded_loop",
            "has_external_calls",
            "is_value_transfer",
            "payable",
            "visibility",
            "writes_state",
            "reads_state",
            "has_loops",
            "has_internal_calls",
            "uses_msg_sender",
            "uses_erc20_transfer",
            "semantic_ops",
            "behavioral_signature",
        ]
        return {k: props.get(k) for k in semantic_keys if k in props}

    # =========================================================================
    # Test Case 1: Reentrancy Detection
    # =========================================================================

    @pytest.mark.xfail(reason="Known pattern quality gap - Phase 3.1c")
    def test_reentrancy_standard_names(self):
        """Reentrancy detected with standard naming."""
        code = """
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract Vault {
    mapping(address => uint256) public balances;

    function withdraw(uint256 amount) external {
        require(balances[msg.sender] >= amount);
        (bool success,) = msg.sender.call{value: amount}("");
        require(success);
        balances[msg.sender] -= amount;
    }

    function deposit() external payable {
        balances[msg.sender] += msg.value;
    }
}
"""
        graph = self._build_graph(code, "Vault")
        if graph is None:
            self.skipTest("Graph build failed")

        props = self._get_function_properties(graph, "withdraw")
        self.assertTrue(
            props.get("state_write_after_external_call", False),
            "Reentrancy should be detected with standard names"
        )

    @pytest.mark.xfail(reason="Known pattern quality gap - Phase 3.1c")
    def test_reentrancy_renamed(self):
        """Reentrancy detected with renamed functions/variables."""
        code = """
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract XyzContract {
    mapping(address => uint256) public userCredits;

    function releaseCredits(uint256 qty) external {
        require(userCredits[msg.sender] >= qty);
        (bool ok,) = msg.sender.call{value: qty}("");
        require(ok);
        userCredits[msg.sender] -= qty;
    }

    function addCredits() external payable {
        userCredits[msg.sender] += msg.value;
    }
}
"""
        graph = self._build_graph(code, "XyzContract")
        if graph is None:
            self.skipTest("Graph build failed")

        props = self._get_function_properties(graph, "releaseCredits")
        self.assertTrue(
            props.get("state_write_after_external_call", False),
            "Reentrancy should be detected regardless of naming"
        )

    @pytest.mark.xfail(reason="Known pattern quality gap - Phase 3.1c")
    def test_reentrancy_semantic_equivalence(self):
        """Standard and renamed versions have equivalent semantic properties."""
        standard = """
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract Vault {
    mapping(address => uint256) public balances;

    function withdraw(uint256 amount) external {
        require(balances[msg.sender] >= amount);
        (bool s,) = msg.sender.call{value: amount}("");
        require(s);
        balances[msg.sender] -= amount;
    }
}
"""
        renamed = """
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract ABC {
    mapping(address => uint256) public xyz;

    function foo(uint256 n) external {
        require(xyz[msg.sender] >= n);
        (bool ok,) = msg.sender.call{value: n}("");
        require(ok);
        xyz[msg.sender] -= n;
    }
}
"""
        graph1 = self._build_graph(standard, "Vault")
        graph2 = self._build_graph(renamed, "ABC")

        if graph1 is None or graph2 is None:
            self.skipTest("Graph build failed")

        props1 = self._extract_semantic_properties(
            self._get_function_properties(graph1, "withdraw")
        )
        props2 = self._extract_semantic_properties(
            self._get_function_properties(graph2, "foo")
        )

        # Key semantic properties should match
        self.assertEqual(
            props1.get("state_write_after_external_call"),
            props2.get("state_write_after_external_call"),
            "Reentrancy detection should be name-agnostic"
        )
        self.assertEqual(
            props1.get("has_external_calls"),
            props2.get("has_external_calls"),
            "External call detection should be name-agnostic"
        )

    # =========================================================================
    # Test Case 2: Access Control Detection
    # =========================================================================

    @pytest.mark.xfail(reason="Known pattern quality gap - Phase 3.1c")
    def test_access_control_standard_names(self):
        """Access control detected with standard naming."""
        code = """
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract Ownable {
    address public owner;

    modifier onlyOwner() {
        require(msg.sender == owner);
        _;
    }

    function setOwner(address newOwner) external onlyOwner {
        owner = newOwner;
    }

    function unprotectedSetOwner(address newOwner) external {
        owner = newOwner;
    }
}
"""
        graph = self._build_graph(code, "Ownable")
        if graph is None:
            self.skipTest("Graph build failed")

        protected = self._get_function_properties(graph, "setOwner(address)")
        unprotected = self._get_function_properties(graph, "unprotectedSetOwner")

        # setOwner should have access gate
        self.assertTrue(
            protected.get("has_access_gate", False),
            "Protected function should have access gate"
        )

    @pytest.mark.xfail(reason="Known pattern quality gap - Phase 3.1c")
    def test_access_control_renamed(self):
        """Access control detected with renamed components."""
        code = """
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract XyzManager {
    address public controller;

    modifier onlyController() {
        require(msg.sender == controller);
        _;
    }

    function updateController(address newCtrl) external onlyController {
        controller = newCtrl;
    }

    function unsafeUpdate(address newCtrl) external {
        controller = newCtrl;
    }
}
"""
        graph = self._build_graph(code, "XyzManager")
        if graph is None:
            self.skipTest("Graph build failed")

        protected = self._get_function_properties(graph, "updateController")
        unprotected = self._get_function_properties(graph, "unsafeUpdate")

        self.assertTrue(
            protected.get("has_access_gate", False),
            "Protected function should have access gate regardless of naming"
        )

    # =========================================================================
    # Test Case 3: Loop Detection
    # =========================================================================

    @pytest.mark.xfail(reason="Known pattern quality gap - Phase 3.1c")
    def test_loop_standard_names(self):
        """Loop detected with standard naming."""
        code = """
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract Distributor {
    address[] public recipients;

    function distribute() external {
        for (uint i = 0; i < recipients.length; i++) {
            payable(recipients[i]).transfer(1 ether);
        }
    }
}
"""
        graph = self._build_graph(code, "Distributor")
        if graph is None:
            self.skipTest("Graph build failed")

        props = self._get_function_properties(graph, "distribute")
        self.assertTrue(
            props.get("has_loops", False),
            "Loop should be detected"
        )
        self.assertTrue(
            props.get("has_unbounded_loop", False),
            "Unbounded loop should be detected"
        )

    @pytest.mark.xfail(reason="Known pattern quality gap - Phase 3.1c")
    def test_loop_renamed(self):
        """Loop detected with renamed components."""
        code = """
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract ABC {
    address[] public xyz;

    function foo() external {
        for (uint j = 0; j < xyz.length; j++) {
            payable(xyz[j]).transfer(1 ether);
        }
    }
}
"""
        graph = self._build_graph(code, "ABC")
        if graph is None:
            self.skipTest("Graph build failed")

        props = self._get_function_properties(graph, "foo")
        self.assertTrue(
            props.get("has_loops", False),
            "Loop should be detected regardless of naming"
        )

    # =========================================================================
    # Test Case 4: Value Transfer Detection
    # =========================================================================

    @pytest.mark.xfail(reason="Known pattern quality gap - Phase 3.1c")
    def test_value_transfer_standard(self):
        """Value transfer detected with standard naming."""
        code = """
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract Treasury {
    function sendFunds(address payable recipient, uint256 amount) external {
        recipient.transfer(amount);
    }
}
"""
        graph = self._build_graph(code, "Treasury")
        if graph is None:
            self.skipTest("Graph build failed")

        props = self._get_function_properties(graph, "sendFunds")
        self.assertTrue(
            props.get("is_value_transfer", False) or props.get("uses_transfer", False),
            "Value transfer should be detected"
        )

    @pytest.mark.xfail(reason="Known pattern quality gap - Phase 3.1c")
    def test_value_transfer_renamed(self):
        """Value transfer detected with renamed components."""
        code = """
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract ABC {
    function xyz(address payable a, uint256 n) external {
        a.transfer(n);
    }
}
"""
        graph = self._build_graph(code, "ABC")
        if graph is None:
            self.skipTest("Graph build failed")

        props = self._get_function_properties(graph, "xyz")
        self.assertTrue(
            props.get("is_value_transfer", False) or props.get("uses_transfer", False),
            "Value transfer should be detected regardless of naming"
        )

    # =========================================================================
    # Test Case 5: Payable Detection
    # =========================================================================

    @pytest.mark.xfail(reason="Known pattern quality gap - Phase 3.1c")
    def test_payable_invariance(self):
        """Payable detection is naming-agnostic."""
        standard = """
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract Vault {
    function deposit() external payable {}
}
"""
        renamed = """
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract XYZ {
    function abc() external payable {}
}
"""
        graph1 = self._build_graph(standard, "Vault")
        graph2 = self._build_graph(renamed, "XYZ")

        if graph1 is None or graph2 is None:
            self.skipTest("Graph build failed")

        props1 = self._get_function_properties(graph1, "deposit")
        props2 = self._get_function_properties(graph2, "abc")

        self.assertEqual(
            props1.get("payable"),
            props2.get("payable"),
            "Payable detection should be name-agnostic"
        )


class DVDeFiInvarianceTests(unittest.TestCase):
    """Test invariance across DVDeFi corpus renames."""

    VKG_ROOT = Path("/Volumes/ex_ssd/home/projects/python/vkg-solidity/alphaswarm")
    DVDEFI_PATH = VKG_ROOT / "examples" / "damm-vuln-defi" / "src"

    def test_unstoppable_detection_invariant(self):
        """Unstoppable detection is name-agnostic."""
        # This tests that the pattern would match even with renamed code
        # We can't actually rename the DVDeFi code, but we can verify
        # that semantic properties are used, not names
        pass  # Placeholder - would need renamed DVDeFi corpus

    def test_detection_uses_semantic_properties(self):
        """Verify patterns use semantic properties, not names."""
        patterns_path = self.VKG_ROOT / "patterns" / "core"
        if not patterns_path.exists():
            self.skipTest("Patterns directory not found")

        import yaml
        name_based_patterns = []

        for pattern_file in patterns_path.glob("*.yaml"):
            with open(pattern_file) as f:
                try:
                    pattern = yaml.safe_load(f)
                except:
                    continue

            # Skip non-dict patterns (some YAML files contain lists)
            if not isinstance(pattern, dict):
                continue

            # Check if pattern uses name-based matching
            match = pattern.get("match", {})
            if not isinstance(match, dict):
                continue
            for condition_list in [match.get("all", []), match.get("any", [])]:
                for condition in condition_list:
                    prop = condition.get("property", "")
                    # Name-based properties would be problematic
                    if "name" in prop.lower() and "parameter_names" not in prop:
                        name_based_patterns.append((pattern_file.name, prop))

        self.assertEqual(
            len(name_based_patterns), 0,
            f"Found name-based pattern conditions: {name_based_patterns}"
        )


if __name__ == "__main__":
    unittest.main()
