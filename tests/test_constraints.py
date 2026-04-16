"""Tests for Phase 11: Constraint-Based Verification.

Tests cover:
- P11-T1: Constraint Extraction
- P11-T2: Z3 Model Building
- P11-T3: Vulnerability Reachability
"""

import unittest
from unittest.mock import MagicMock, PropertyMock

from alphaswarm_sol.kg.constraints import (
    ConstraintType,
    SourceLocation,
    Constraint,
    StateVariable,
    PathCondition,
    extract_variables,
    extract_constraints_from_node,
    extract_constraints,
    extract_state_variables,
    Z3ModelBuilder,
    build_z3_model,
    check_vulnerability_reachable,
    VulnerabilityCheck,
    ConstraintVerifier,
    Z3_AVAILABLE,
)


class TestConstraintTypes(unittest.TestCase):
    """Tests for constraint type definitions."""

    def test_constraint_type_values(self):
        """Test that constraint types have expected values."""
        self.assertEqual(ConstraintType.BRANCH.value, "branch")
        self.assertEqual(ConstraintType.REQUIRE.value, "require")
        self.assertEqual(ConstraintType.ASSERT.value, "assert")
        self.assertEqual(ConstraintType.LOOP_BOUND.value, "loop_bound")

    def test_source_location(self):
        """Test SourceLocation dataclass."""
        loc = SourceLocation(
            file="test.sol",
            line_start=10,
            line_end=15,
            column_start=0,
            column_end=50,
        )
        self.assertEqual(loc.file, "test.sol")
        self.assertEqual(loc.line_start, 10)

        data = loc.to_dict()
        self.assertEqual(data["file"], "test.sol")
        self.assertEqual(data["line_start"], 10)

    def test_constraint_creation(self):
        """Test Constraint dataclass creation."""
        constraint = Constraint(
            type=ConstraintType.REQUIRE,
            expression="amount > 0",
            variables={"amount"},
            location=SourceLocation(file="test.sol", line_start=10),
            negated=False,
        )
        self.assertEqual(constraint.type, ConstraintType.REQUIRE)
        self.assertEqual(constraint.expression, "amount > 0")
        self.assertIn("amount", constraint.variables)

    def test_constraint_to_dict(self):
        """Test Constraint serialization."""
        constraint = Constraint(
            type=ConstraintType.BRANCH,
            expression="x == 10",
            variables={"x"},
        )
        data = constraint.to_dict()
        self.assertEqual(data["type"], "branch")
        self.assertEqual(data["expression"], "x == 10")
        self.assertIn("x", data["variables"])

    def test_state_variable(self):
        """Test StateVariable dataclass."""
        var = StateVariable(
            name="balance",
            var_type="uint256",
            is_mapping=False,
            initial_value=0,
        )
        self.assertEqual(var.name, "balance")
        self.assertEqual(var.var_type, "uint256")

        data = var.to_dict()
        self.assertEqual(data["name"], "balance")

    def test_path_condition(self):
        """Test PathCondition dataclass."""
        path = PathCondition(
            path_id="path_1",
            constraints=[
                Constraint(
                    type=ConstraintType.REQUIRE,
                    expression="x > 0",
                    variables={"x"},
                )
            ],
            reachable=True,
            model={"x": "5"},
        )
        self.assertEqual(path.path_id, "path_1")
        self.assertTrue(path.reachable)

        data = path.to_dict()
        self.assertEqual(len(data["constraints"]), 1)


class TestExtractVariables(unittest.TestCase):
    """Tests for variable extraction from expressions."""

    def test_simple_variable(self):
        """Test extracting a single variable."""
        variables = extract_variables("x > 0")
        self.assertIn("x", variables)

    def test_multiple_variables(self):
        """Test extracting multiple variables."""
        variables = extract_variables("x > 0 && y < 10")
        self.assertIn("x", variables)
        self.assertIn("y", variables)

    def test_excludes_keywords(self):
        """Test that Solidity keywords are excluded."""
        variables = extract_variables("msg.sender == owner")
        self.assertNotIn("msg", variables)
        self.assertNotIn("sender", variables)
        self.assertIn("owner", variables)

    def test_complex_expression(self):
        """Test complex expression."""
        variables = extract_variables("balance >= amount && allowed[msg.sender] > threshold")
        self.assertIn("balance", variables)
        self.assertIn("amount", variables)
        self.assertIn("allowed", variables)
        self.assertIn("threshold", variables)


class TestConstraintExtraction(unittest.TestCase):
    """Tests for constraint extraction from nodes."""

    def create_mock_node(
        self,
        node_type: str,
        expression: str = "",
        has_source_mapping: bool = True,
    ) -> MagicMock:
        """Create a mock Slither node."""
        node = MagicMock()

        # Create type mock
        type_mock = MagicMock()
        type_mock.name = node_type
        node.type = type_mock

        # Set expression
        if expression:
            expr_mock = MagicMock()
            expr_mock.__str__ = lambda s: expression
            node.expression = expr_mock
        else:
            node.expression = None

        # Source mapping
        if has_source_mapping:
            sm = MagicMock()
            sm.filename_short = "test.sol"
            sm.lines = [10, 11]
            node.source_mapping = sm
        else:
            del node.source_mapping

        return node

    def test_extract_if_constraint(self):
        """Test extracting constraint from IF node."""
        node = self.create_mock_node("IF", "x > 10")
        constraints = extract_constraints_from_node(node)

        self.assertEqual(len(constraints), 1)
        self.assertEqual(constraints[0].type, ConstraintType.BRANCH)
        self.assertEqual(constraints[0].expression, "x > 10")

    def test_extract_require_constraint(self):
        """Test extracting constraint from require statement."""
        node = self.create_mock_node("EXPRESSION", "require(amount > 0, 'Amount must be positive')")
        constraints = extract_constraints_from_node(node)

        self.assertEqual(len(constraints), 1)
        self.assertEqual(constraints[0].type, ConstraintType.REQUIRE)
        self.assertIn("amount", constraints[0].expression)

    def test_extract_assert_constraint(self):
        """Test extracting constraint from assert statement."""
        node = self.create_mock_node("EXPRESSION", "assert(balance >= 0)")
        constraints = extract_constraints_from_node(node)

        self.assertEqual(len(constraints), 1)
        self.assertEqual(constraints[0].type, ConstraintType.ASSERT)

    def test_extract_loop_constraint(self):
        """Test extracting constraint from loop."""
        node = self.create_mock_node("BEGIN_LOOP", "i < length")
        constraints = extract_constraints_from_node(node)

        self.assertEqual(len(constraints), 1)
        self.assertEqual(constraints[0].type, ConstraintType.LOOP_BOUND)

    def test_extract_no_constraint(self):
        """Test node with no constraint."""
        node = self.create_mock_node("RETURN", "")
        constraints = extract_constraints_from_node(node)
        self.assertEqual(len(constraints), 0)


class TestExtractConstraintsFromFunction(unittest.TestCase):
    """Tests for extracting constraints from entire functions."""

    def create_mock_function(self, node_specs: list) -> MagicMock:
        """Create a mock function with specified nodes."""
        function = MagicMock()
        nodes = []

        for spec in node_specs:
            node = MagicMock()
            type_mock = MagicMock()
            type_mock.name = spec["type"]
            node.type = type_mock

            if "expression" in spec:
                expr_mock = MagicMock()
                expr_mock.__str__ = lambda s, e=spec["expression"]: e
                node.expression = expr_mock
            else:
                node.expression = None

            nodes.append(node)

        function.nodes = nodes
        return function

    def test_extract_multiple_constraints(self):
        """Test extracting multiple constraints from function."""
        function = self.create_mock_function([
            {"type": "EXPRESSION", "expression": "require(x > 0)"},
            {"type": "IF", "expression": "y < 100"},
            {"type": "EXPRESSION", "expression": "balance = x + y"},
        ])

        constraints = extract_constraints(function)
        self.assertGreaterEqual(len(constraints), 2)

    def test_function_without_nodes(self):
        """Test function without nodes attribute."""
        function = MagicMock(spec=[])  # No nodes attribute
        constraints = extract_constraints(function)
        self.assertEqual(len(constraints), 0)


class TestStateVariableExtraction(unittest.TestCase):
    """Tests for state variable extraction."""

    def test_extract_state_variables(self):
        """Test extracting state variables from contract."""
        contract = MagicMock()
        var1 = MagicMock()
        var1.name = "balance"
        var1.type = "uint256"

        var2 = MagicMock()
        var2.name = "owner"
        var2.type = "address"

        var3 = MagicMock()
        var3.name = "allowances"
        var3.type = "mapping(address => uint256)"

        contract.state_variables = [var1, var2, var3]

        state_vars = extract_state_variables(contract)

        self.assertEqual(len(state_vars), 3)
        self.assertEqual(state_vars[0].name, "balance")
        self.assertEqual(state_vars[1].name, "owner")
        self.assertTrue(state_vars[2].is_mapping)


@unittest.skipUnless(Z3_AVAILABLE, "Z3 not available")
class TestZ3ModelBuilder(unittest.TestCase):
    """Tests for Z3 model building."""

    def test_create_builder(self):
        """Test creating Z3 model builder."""
        builder = Z3ModelBuilder()
        self.assertIsNotNone(builder.solver)
        self.assertEqual(len(builder.z3_vars), 0)

    def test_add_uint_variable(self):
        """Test adding uint variable."""
        builder = Z3ModelBuilder()
        var = StateVariable(name="balance", var_type="uint256")
        z3_var = builder.add_state_variable(var)

        self.assertIsNotNone(z3_var)
        self.assertIn("balance", builder.z3_vars)

    def test_add_bool_variable(self):
        """Test adding bool variable."""
        builder = Z3ModelBuilder()
        var = StateVariable(name="paused", var_type="bool")
        z3_var = builder.add_state_variable(var)

        self.assertIsNotNone(z3_var)
        self.assertIn("paused", builder.z3_vars)

    def test_add_address_variable(self):
        """Test adding address variable."""
        builder = Z3ModelBuilder()
        var = StateVariable(name="owner", var_type="address")
        z3_var = builder.add_state_variable(var)

        self.assertIsNotNone(z3_var)
        self.assertIn("owner", builder.z3_vars)

    def test_add_simple_constraint(self):
        """Test adding simple constraint."""
        builder = Z3ModelBuilder()
        constraint = Constraint(
            type=ConstraintType.REQUIRE,
            expression="x > 0",
            variables={"x"},
        )
        result = builder.add_constraint(constraint)
        self.assertTrue(result)

    def test_check_satisfiability_sat(self):
        """Test satisfiability check - SAT case."""
        builder = Z3ModelBuilder()
        builder.add_constraint(Constraint(
            type=ConstraintType.REQUIRE,
            expression="x > 0",
            variables={"x"},
        ))

        result, model = builder.check_satisfiability()
        self.assertEqual(result, "sat")
        self.assertIsNotNone(model)

    def test_check_satisfiability_unsat(self):
        """Test satisfiability check - UNSAT case."""
        builder = Z3ModelBuilder()
        # Add contradictory constraints
        builder.add_constraint(Constraint(
            type=ConstraintType.REQUIRE,
            expression="x > 10",
            variables={"x"},
        ))
        builder.add_constraint(Constraint(
            type=ConstraintType.REQUIRE,
            expression="x < 5",
            variables={"x"},
        ))

        result, model = builder.check_satisfiability()
        self.assertEqual(result, "unsat")
        self.assertIsNone(model)

    def test_push_pop(self):
        """Test push/pop solver state."""
        builder = Z3ModelBuilder()
        builder.add_constraint(Constraint(
            type=ConstraintType.REQUIRE,
            expression="x > 0",
            variables={"x"},
        ))

        builder.push()
        builder.add_constraint(Constraint(
            type=ConstraintType.REQUIRE,
            expression="x < 0",
            variables={"x"},
        ))

        # Should be UNSAT now
        result, _ = builder.check_satisfiability()
        self.assertEqual(result, "unsat")

        # Pop should restore SAT state
        builder.pop()
        result, _ = builder.check_satisfiability()
        self.assertEqual(result, "sat")

    def test_reset(self):
        """Test resetting the builder."""
        builder = Z3ModelBuilder()
        builder.add_state_variable(StateVariable(name="x", var_type="uint256"))
        builder.add_constraint(Constraint(
            type=ConstraintType.REQUIRE,
            expression="x > 0",
            variables={"x"},
        ))

        self.assertGreater(len(builder.z3_vars), 0)

        builder.reset()
        self.assertEqual(len(builder.z3_vars), 0)


@unittest.skipUnless(Z3_AVAILABLE, "Z3 not available")
class TestBuildZ3Model(unittest.TestCase):
    """Tests for build_z3_model function."""

    def test_build_model(self):
        """Test building Z3 model from constraints and variables."""
        constraints = [
            Constraint(
                type=ConstraintType.REQUIRE,
                expression="balance >= amount",
                variables={"balance", "amount"},
            )
        ]
        state_vars = [
            StateVariable(name="balance", var_type="uint256"),
            StateVariable(name="amount", var_type="uint256"),
        ]

        builder, z3_vars = build_z3_model(constraints, state_vars)

        self.assertIsNotNone(builder)
        self.assertIn("balance", z3_vars)
        self.assertIn("amount", z3_vars)


@unittest.skipUnless(Z3_AVAILABLE, "Z3 not available")
class TestVulnerabilityReachability(unittest.TestCase):
    """Tests for vulnerability reachability checking."""

    def test_reachable_vulnerability(self):
        """Test detecting reachable vulnerability."""
        builder = Z3ModelBuilder()
        builder.add_state_variable(StateVariable(name="balance", var_type="uint256"))
        builder.add_state_variable(StateVariable(name="amount", var_type="uint256"))

        # Add constraint: balance > 0
        builder.add_constraint(Constraint(
            type=ConstraintType.REQUIRE,
            expression="balance > 0",
            variables={"balance"},
        ))

        # Check if balance can be 0 (vulnerability condition)
        is_reachable, model = check_vulnerability_reachable(
            builder, "amount > balance"
        )

        # This should be reachable (amount can be > balance)
        self.assertTrue(is_reachable)
        self.assertIsNotNone(model)

    def test_unreachable_vulnerability(self):
        """Test detecting unreachable vulnerability."""
        builder = Z3ModelBuilder()
        builder.add_state_variable(StateVariable(name="x", var_type="uint256"))

        # Add constraint: x >= 10
        builder.add_constraint(Constraint(
            type=ConstraintType.REQUIRE,
            expression="x >= 10",
            variables={"x"},
        ))

        # Check if x can be negative (impossible for uint with x >= 10)
        is_reachable, model = check_vulnerability_reachable(
            builder, "x < 0"
        )

        self.assertFalse(is_reachable)
        self.assertIsNone(model)


class TestVulnerabilityCheck(unittest.TestCase):
    """Tests for VulnerabilityCheck dataclass."""

    def test_vulnerability_check_creation(self):
        """Test creating VulnerabilityCheck."""
        check = VulnerabilityCheck(
            vuln_type="integer_overflow",
            condition="result > MAX_UINT256",
            is_reachable=True,
            model={"result": "340282366920938463463374607431768211456"},
            confidence=1.0,
        )

        self.assertEqual(check.vuln_type, "integer_overflow")
        self.assertTrue(check.is_reachable)
        self.assertEqual(check.confidence, 1.0)

    def test_vulnerability_check_to_dict(self):
        """Test VulnerabilityCheck serialization."""
        check = VulnerabilityCheck(
            vuln_type="division_by_zero",
            condition="divisor == 0",
            is_reachable=True,
            model={"divisor": "0"},
        )

        data = check.to_dict()
        self.assertEqual(data["vuln_type"], "division_by_zero")
        self.assertTrue(data["is_reachable"])


@unittest.skipUnless(Z3_AVAILABLE, "Z3 not available")
class TestConstraintVerifier(unittest.TestCase):
    """Tests for ConstraintVerifier class."""

    def test_verifier_creation(self):
        """Test creating ConstraintVerifier."""
        verifier = ConstraintVerifier()
        self.assertIsNone(verifier.builder)
        self.assertEqual(len(verifier.constraints), 0)

    def test_check_vulnerability_without_z3(self):
        """Test vulnerability check returns low confidence without model."""
        verifier = ConstraintVerifier()
        # Don't build model

        result = verifier.check_vulnerability("integer_overflow")
        self.assertFalse(result.is_reachable)
        self.assertEqual(result.confidence, 0.0)

    def test_check_vulnerability_with_model(self):
        """Test vulnerability check with Z3 model."""
        verifier = ConstraintVerifier()

        # Manually set up state
        verifier.state_vars = [
            StateVariable(name="divisor", var_type="uint256"),
        ]
        verifier.constraints = [
            Constraint(
                type=ConstraintType.REQUIRE,
                expression="divisor >= 0",
                variables={"divisor"},
            )
        ]

        # Build model
        success = verifier.build_model()
        self.assertTrue(success)

        # Check for division by zero (should be reachable)
        result = verifier.check_vulnerability("division_by_zero")
        self.assertTrue(result.is_reachable)

    def test_check_all_vulnerabilities(self):
        """Test checking all vulnerability types."""
        verifier = ConstraintVerifier()
        verifier.state_vars = [
            StateVariable(name="x", var_type="uint256"),
        ]
        verifier.constraints = []
        verifier.build_model()

        results = verifier.check_all_vulnerabilities()

        # Should have results for all known vulnerability types
        self.assertGreater(len(results), 0)
        vuln_types = {r.vuln_type for r in results}
        self.assertIn("integer_overflow", vuln_types)
        self.assertIn("division_by_zero", vuln_types)


class TestConstraintWithoutZ3(unittest.TestCase):
    """Tests that work without Z3 installed."""

    def test_constraint_extraction_no_z3(self):
        """Test that constraint extraction works without Z3."""
        # This should work regardless of Z3 availability
        constraint = Constraint(
            type=ConstraintType.REQUIRE,
            expression="x > 0",
            variables={"x"},
        )
        self.assertEqual(constraint.expression, "x > 0")

    def test_extract_variables_no_z3(self):
        """Test variable extraction works without Z3."""
        variables = extract_variables("a + b > c")
        self.assertIn("a", variables)
        self.assertIn("b", variables)
        self.assertIn("c", variables)


if __name__ == "__main__":
    unittest.main()
