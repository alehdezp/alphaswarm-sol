"""
Property Test Template

This template provides a standardized way to test builder.py properties.
Copy this file and rename it to test_property_<property_name>.py.

Each property test should include:
1. True Positives (TP) - Cases where property should be True
2. True Negatives (TN) - Cases where property should be False
3. Edge Cases - Boundary conditions
4. Variations - Different code patterns that should trigger/not trigger

Usage:
    1. Copy this template
    2. Replace PROPERTY_NAME with actual property name
    3. Replace CONTRACT_CODE with test Solidity code
    4. Run: uv run pytest tests/test_property_<name>.py -v
"""

import unittest
from tests.graph_cache import load_graph_from_source


# ============================================================================
# Configuration - Modify these for your property
# ============================================================================

PROPERTY_NAME = "has_example_property"  # Replace with actual property name
PROPERTY_CATEGORY = "access"  # access, state, external, loops, tokens, oracle, crypto


# ============================================================================
# Test Contracts - Define Solidity code for each test case
# ============================================================================

# True Positive: Property should be True
TP_CONTRACT_1 = """
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract TruePositive1 {
    // This contract should have PROPERTY_NAME = true

    function vulnerableFunction() external {
        // Code that triggers the property
    }
}
"""

TP_CONTRACT_2 = """
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract TruePositive2 {
    // Alternative pattern that should also trigger property

    function anotherVulnerableFunction() public {
        // Different code that also triggers the property
    }
}
"""

# True Negative: Property should be False
TN_CONTRACT_1 = """
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract TrueNegative1 {
    // This contract should have PROPERTY_NAME = false

    function safeFunction() external {
        // Code that does NOT trigger the property
    }
}
"""

TN_CONTRACT_2 = """
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract TrueNegative2 {
    // Similar to TN_CONTRACT_1 but different pattern

    function anotherSafeFunction() public {
        // Different safe code
    }
}
"""

# Edge Cases: Boundary conditions
EDGE_CONTRACT_1 = """
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract EdgeCase1 {
    // Edge case: internal function (should not match if property requires external)

    function internalFunction() internal {
        // Internal functions have different rules
    }
}
"""

EDGE_CONTRACT_2 = """
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract EdgeCase2 {
    // Edge case: empty function

    function emptyFunction() external {
        // No code - edge case
    }
}
"""

# Variations: Different naming/patterns that should have same result
VAR_CONTRACT_1 = """
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract Variation1 {
    // Variation: completely different names

    function xyz() external {
        // Same behavior, different names
    }
}
"""

VAR_CONTRACT_2 = """
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract Variation2 {
    // Variation: different code structure, same semantics

    function abc() external {
        // Different structure
    }
}
"""


# ============================================================================
# Test Class - Standard test structure
# ============================================================================

class TestProperty(unittest.TestCase):
    """
    Tests for PROPERTY_NAME builder property.

    Property Description:
        [Add description of what this property detects]

    Expected Behavior:
        - True when: [describe conditions]
        - False when: [describe conditions]

    Related Patterns:
        - [list patterns that use this property]
    """

    # -------------------------------------------------------------------------
    # True Positive Tests
    # -------------------------------------------------------------------------

    def test_tp1_basic_case(self):
        """PROPERTY_NAME should be True for basic vulnerable pattern."""
        graph = load_graph_from_source(TP_CONTRACT_1, "TruePositive1")
        func = self._find_function(graph, "vulnerableFunction")

        self.assertIsNotNone(func, "Function not found in graph")
        self.assertTrue(
            func["properties"].get(PROPERTY_NAME, False),
            f"{PROPERTY_NAME} should be True for vulnerableFunction"
        )

    def test_tp2_alternative_pattern(self):
        """PROPERTY_NAME should be True for alternative vulnerable pattern."""
        graph = load_graph_from_source(TP_CONTRACT_2, "TruePositive2")
        func = self._find_function(graph, "anotherVulnerableFunction")

        self.assertIsNotNone(func, "Function not found in graph")
        self.assertTrue(
            func["properties"].get(PROPERTY_NAME, False),
            f"{PROPERTY_NAME} should be True for anotherVulnerableFunction"
        )

    # -------------------------------------------------------------------------
    # True Negative Tests
    # -------------------------------------------------------------------------

    def test_tn1_safe_pattern(self):
        """PROPERTY_NAME should be False for safe pattern."""
        graph = load_graph_from_source(TN_CONTRACT_1, "TrueNegative1")
        func = self._find_function(graph, "safeFunction")

        self.assertIsNotNone(func, "Function not found in graph")
        self.assertFalse(
            func["properties"].get(PROPERTY_NAME, False),
            f"{PROPERTY_NAME} should be False for safeFunction"
        )

    def test_tn2_alternative_safe_pattern(self):
        """PROPERTY_NAME should be False for alternative safe pattern."""
        graph = load_graph_from_source(TN_CONTRACT_2, "TrueNegative2")
        func = self._find_function(graph, "anotherSafeFunction")

        self.assertIsNotNone(func, "Function not found in graph")
        self.assertFalse(
            func["properties"].get(PROPERTY_NAME, False),
            f"{PROPERTY_NAME} should be False for anotherSafeFunction"
        )

    # -------------------------------------------------------------------------
    # Edge Case Tests
    # -------------------------------------------------------------------------

    def test_edge1_internal_function(self):
        """PROPERTY_NAME behavior for internal functions."""
        graph = load_graph_from_source(EDGE_CONTRACT_1, "EdgeCase1")
        func = self._find_function(graph, "internalFunction")

        # Define expected behavior for edge case
        # self.assertEqual(func["properties"].get(PROPERTY_NAME, False), expected_value)
        pass  # Implement based on property semantics

    def test_edge2_empty_function(self):
        """PROPERTY_NAME behavior for empty functions."""
        graph = load_graph_from_source(EDGE_CONTRACT_2, "EdgeCase2")
        func = self._find_function(graph, "emptyFunction")

        # Define expected behavior for edge case
        pass  # Implement based on property semantics

    # -------------------------------------------------------------------------
    # Variation Tests (Name Agnostic)
    # -------------------------------------------------------------------------

    def test_var1_different_names(self):
        """PROPERTY_NAME should work regardless of function/variable names."""
        graph = load_graph_from_source(VAR_CONTRACT_1, "Variation1")
        func = self._find_function(graph, "xyz")

        # Should have same result as TP or TN depending on semantics
        pass  # Implement based on property semantics

    def test_var2_different_structure(self):
        """PROPERTY_NAME should work with different code structures."""
        graph = load_graph_from_source(VAR_CONTRACT_2, "Variation2")
        func = self._find_function(graph, "abc")

        # Should have same result regardless of code structure
        pass  # Implement based on property semantics

    # -------------------------------------------------------------------------
    # Helper Methods
    # -------------------------------------------------------------------------

    def _find_function(self, graph, func_name: str):
        """Find a function node by name in the graph."""
        for node in graph.get("graph", {}).get("nodes", []):
            if node.get("type") == "Function":
                label = node.get("label", "")
                # Match function name (may include parameters)
                if func_name in label or label.startswith(f"{func_name}("):
                    return node
        return None

    def _get_property(self, node, property_name: str, default=None):
        """Safely get a property from a node."""
        return node.get("properties", {}).get(property_name, default)


# ============================================================================
# Metrics Collection (Optional)
# ============================================================================

class PropertyMetrics:
    """
    Collect and report metrics for property testing.

    Use to track:
    - Number of TP/TN/FP/FN cases
    - Precision and recall
    - Edge case coverage
    """

    def __init__(self):
        self.tp_count = 0
        self.tn_count = 0
        self.fp_count = 0
        self.fn_count = 0

    def record_tp(self):
        self.tp_count += 1

    def record_tn(self):
        self.tn_count += 1

    def record_fp(self):
        self.fp_count += 1

    def record_fn(self):
        self.fn_count += 1

    @property
    def precision(self) -> float:
        if self.tp_count + self.fp_count == 0:
            return 0.0
        return self.tp_count / (self.tp_count + self.fp_count)

    @property
    def recall(self) -> float:
        if self.tp_count + self.fn_count == 0:
            return 0.0
        return self.tp_count / (self.tp_count + self.fn_count)

    @property
    def f1_score(self) -> float:
        if self.precision + self.recall == 0:
            return 0.0
        return 2 * (self.precision * self.recall) / (self.precision + self.recall)

    def report(self) -> str:
        return f"""
Property Metrics:
  TP: {self.tp_count}, TN: {self.tn_count}, FP: {self.fp_count}, FN: {self.fn_count}
  Precision: {self.precision:.2%}
  Recall: {self.recall:.2%}
  F1 Score: {self.f1_score:.2%}
"""


if __name__ == "__main__":
    unittest.main()
