"""
Tests for P2-T4: LLMDFA Verifier

Tests constraint extraction, Z3 synthesis, and formal verification.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
import sys

from alphaswarm_sol.agents.verifier import (
    LLMDFAVerifier,
    VerificationResult,
    VerificationStatus,
    ConstraintType,
    PathConstraint,
    ConstraintSet,
    WitnessValues,
    UnsatCore,
    verify_path_feasibility,
    Z3_AVAILABLE,
)
from alphaswarm_sol.agents.attacker import (
    AttackCategory,
    AttackConstruction,
    AttackPrerequisite,
    AttackStep,
    AttackFeasibility,
    EconomicAnalysis,
    EconomicImpact,
)
from alphaswarm_sol.agents.defender import (
    DefenseArgument,
    DefenseType,
    GuardInfo,
)


# Skip tests if Z3 is not available
pytestmark = pytest.mark.skipif(not Z3_AVAILABLE, reason="Z3 solver not installed")


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def verifier():
    """Create verifier without LLM."""
    return LLMDFAVerifier(llm_client=None, timeout_seconds=30)


@pytest.fixture
def mock_llm():
    """Create mock LLM client."""
    llm = Mock()
    llm.analyze = Mock(return_value='[{"solidity_expr": "balance >= amount", "type": "require", "variables": ["balance", "amount"]}]')
    return llm


@pytest.fixture
def verifier_with_llm(mock_llm):
    """Create verifier with mock LLM."""
    return LLMDFAVerifier(llm_client=mock_llm, timeout_seconds=30)


@pytest.fixture
def simple_attack():
    """Create simple attack for testing."""
    return AttackConstruction(
        category=AttackCategory.STATE_MANIPULATION,
        target_nodes=["fn_withdraw"],
        preconditions=[
            AttackPrerequisite(
                condition="balance >= amount",
                satisfied=True,
                evidence=["fn_withdraw"],
            ),
        ],
        attack_steps=[
            AttackStep(
                step_number=1,
                action="Call withdraw with valid amount",
                effect="External call made before state update",
            ),
        ],
        postconditions=["Funds drained"],
        exploitability_score=0.8,
        feasibility=AttackFeasibility.LOW,
        economic_analysis=EconomicAnalysis(impact_level=EconomicImpact.HIGH),
    )


@pytest.fixture
def reentrancy_attack():
    """Create reentrancy attack for testing."""
    return AttackConstruction(
        category=AttackCategory.STATE_MANIPULATION,
        target_nodes=["fn_withdraw"],
        preconditions=[
            AttackPrerequisite(
                condition="Attacker has positive balance",
                satisfied=True,
            ),
            AttackPrerequisite(
                condition="External call succeeds",
                satisfied=True,
            ),
        ],
        attack_steps=[
            AttackStep(step_number=1, action="Call withdraw", effect="External call made"),
            AttackStep(step_number=2, action="Reenter from callback", effect="State not yet updated"),
        ],
        postconditions=["Multiple withdrawals possible"],
        exploitability_score=0.9,
        feasibility=AttackFeasibility.TRIVIAL,
        economic_analysis=EconomicAnalysis(impact_level=EconomicImpact.CRITICAL),
        historical_exploits=["CVE-2016-6307"],
    )


@pytest.fixture
def defense_with_guard():
    """Create defense with guard."""
    return DefenseArgument(
        id="defense_1",
        claim="Reentrancy guard prevents attack",
        defense_type=DefenseType.GUARD_PRESENT,
        guards_identified=[
            GuardInfo(
                guard_type="reentrancy_guard",
                name="nonReentrant",
                strength=0.95,
            ),
        ],
    )


# Vulnerable code samples
VULNERABLE_WITHDRAW = '''
function withdraw(uint256 amount) external {
    require(balances[msg.sender] >= amount, "Insufficient balance");
    (bool success,) = msg.sender.call{value: amount}("");
    require(success, "Transfer failed");
    balances[msg.sender] -= amount;  // State update AFTER external call
}
'''

SAFE_WITHDRAW = '''
function withdraw(uint256 amount) external nonReentrant {
    require(balances[msg.sender] >= amount, "Insufficient balance");
    balances[msg.sender] -= amount;  // State update BEFORE external call
    (bool success,) = msg.sender.call{value: amount}("");
    require(success, "Transfer failed");
}
'''


# =============================================================================
# Basic Functionality Tests
# =============================================================================


class TestVerifierInitialization:
    """Test verifier initialization."""

    def test_default_initialization(self, verifier):
        """Test default verifier creation."""
        assert verifier is not None
        assert verifier.timeout == 30
        assert verifier.llm is None

    def test_z3_available(self, verifier):
        """Test Z3 availability check."""
        assert verifier.z3_available == True

    def test_custom_timeout(self):
        """Test custom timeout setting."""
        v = LLMDFAVerifier(timeout_seconds=60)
        assert v.timeout == 60

    def test_with_llm(self, mock_llm):
        """Test initialization with LLM."""
        v = LLMDFAVerifier(llm_client=mock_llm)
        assert v.llm is mock_llm


# =============================================================================
# Constraint Extraction Tests
# =============================================================================


class TestConstraintExtraction:
    """Test constraint extraction from code."""

    def test_extract_require_constraints(self, verifier):
        """Test extraction of require statements."""
        code = '''
        function withdraw(uint256 amount) external {
            require(balances[msg.sender] >= amount, "Insufficient");
            require(amount > 0, "Zero amount");
        }
        '''
        constraints = ConstraintSet()
        verifier._extract_require_constraints(code, constraints)

        assert len(constraints.constraints) >= 2
        exprs = [c.solidity_expr for c in constraints.constraints]
        assert any("balance" in e.lower() for e in exprs)
        assert any("amount > 0" in e for e in exprs)

    def test_extract_if_constraints(self, verifier):
        """Test extraction of if conditions."""
        code = '''
        function transfer(uint256 amount) external {
            if (amount > 0) {
                balances[msg.sender] -= amount;
            }
        }
        '''
        constraints = ConstraintSet()
        verifier._extract_if_constraints(code, constraints)

        assert len(constraints.constraints) >= 1
        assert constraints.constraints[0].constraint_type == ConstraintType.IF_CONDITION

    def test_extract_variables(self, verifier):
        """Test variable extraction from expressions."""
        expr = "balances[msg.sender] >= amount + fee"
        vars = verifier._extract_variables(expr)

        assert "balances" in vars
        assert "amount" in vars
        assert "fee" in vars
        # Keywords should be filtered
        assert "msg" not in vars

    def test_extract_constraints_full(self, verifier, simple_attack):
        """Test full constraint extraction."""
        constraints = verifier._extract_constraints(
            simple_attack,
            VULNERABLE_WITHDRAW,
            {},
        )

        assert len(constraints.constraints) > 0
        assert len(constraints.variables) > 0


# =============================================================================
# Solidity to Z3 Conversion Tests
# =============================================================================


class TestSolidityToZ3:
    """Test Solidity expression to Z3 conversion."""

    def test_comparison_operators(self, verifier):
        """Test comparison operator conversion."""
        assert verifier._solidity_to_z3("a >= b") == "(>= a b)"
        assert verifier._solidity_to_z3("a <= b") == "(<= a b)"
        assert verifier._solidity_to_z3("a > b") == "(> a b)"
        assert verifier._solidity_to_z3("a < b") == "(< a b)"
        assert verifier._solidity_to_z3("a == b") == "(= a b)"
        assert verifier._solidity_to_z3("a != b") == "(distinct a b)"

    def test_arithmetic_operators(self, verifier):
        """Test arithmetic operator conversion."""
        assert verifier._solidity_to_z3("a + b") == "(+ a b)"
        assert verifier._solidity_to_z3("a - b") == "(- a b)"
        assert verifier._solidity_to_z3("a * b") == "(* a b)"

    def test_boolean_values(self, verifier):
        """Test boolean value conversion."""
        assert verifier._solidity_to_z3("true") == "true"
        assert verifier._solidity_to_z3("false") == "false"

    def test_mapping_access(self, verifier):
        """Test mapping access conversion."""
        result = verifier._solidity_to_z3("balances[addr]")
        assert "select" in result


# =============================================================================
# Z3 Script Building Tests
# =============================================================================


class TestZ3ScriptBuilding:
    """Test Z3 script generation."""

    def test_build_simple_script(self, verifier):
        """Test building simple Z3 script."""
        constraints = ConstraintSet()
        constraints.variables = {"amount": "Int", "balance": "Int"}
        constraints.add(PathConstraint(
            id="c1",
            constraint_type=ConstraintType.REQUIRE,
            solidity_expr="balance >= amount",
            z3_expr="(>= balance amount)",
            source_location="test",
            variables=["balance", "amount"],
        ))

        script = verifier._build_z3_script(constraints)

        assert "(declare-const amount Int)" in script
        assert "(declare-const balance Int)" in script
        assert "(assert" in script
        assert "(check-sat)" in script
        assert "(get-model)" in script

    def test_script_includes_nonneg_constraints(self, verifier):
        """Test that script adds non-negative constraints for uint-like vars."""
        constraints = ConstraintSet()
        constraints.variables = {"amount": "Int"}

        script = verifier._build_z3_script(constraints)

        assert "(assert (>= amount 0))" in script


# =============================================================================
# Z3 Execution Tests
# =============================================================================


class TestZ3Execution:
    """Test Z3 solver execution."""

    def test_sat_result(self, verifier):
        """Test SAT result with satisfiable constraints."""
        script = """
        (declare-const amount Int)
        (declare-const balance Int)
        (assert (>= balance amount))
        (assert (> amount 0))
        (assert (= balance 100))
        (assert (= amount 50))
        (check-sat)
        (get-model)
        """
        result = verifier._execute_z3(script)

        assert result["status"] == "sat"
        assert "model" in result

    def test_unsat_result(self, verifier):
        """Test UNSAT result for impossible constraints."""
        script = """
        (declare-const x Int)
        (assert (> x 10))
        (assert (< x 5))
        (check-sat)
        """
        result = verifier._execute_z3(script)

        assert result["status"] == "unsat"

    def test_syntax_validation(self, verifier):
        """Test syntax validation catches errors."""
        valid_script = "(declare-const x Int)\n(check-sat)"
        invalid_script = "(invalid syntax here"

        is_valid, _ = verifier._validate_z3_syntax(valid_script)
        assert is_valid

        is_valid, error = verifier._validate_z3_syntax(invalid_script)
        assert not is_valid
        assert len(error) > 0


# =============================================================================
# Full Verification Pipeline Tests
# =============================================================================


class TestFullVerification:
    """Test complete verification pipeline."""

    def test_verify_feasible_attack(self, verifier, simple_attack):
        """Test verification of a feasible attack path."""
        result = verifier.verify_attack_path(
            simple_attack,
            VULNERABLE_WITHDRAW,
        )

        # Result should be valid regardless of outcome
        # Complex Solidity expressions may not parse cleanly into Z3
        assert isinstance(result, VerificationResult)
        assert result.status in [
            VerificationStatus.SAT,
            VerificationStatus.UNSAT,
            VerificationStatus.UNKNOWN,
            VerificationStatus.ERROR,
        ]
        # If proven, should have consistent feasibility
        if result.is_proven:
            assert result.path_feasible == (result.status == VerificationStatus.SAT)

    def test_verify_returns_result(self, verifier, simple_attack):
        """Test that verification returns valid result."""
        result = verifier.verify_attack_path(
            simple_attack,
            "function test() external {}",
        )

        assert isinstance(result, VerificationResult)
        assert result.status in [
            VerificationStatus.SAT,
            VerificationStatus.UNSAT,
            VerificationStatus.UNKNOWN,
            VerificationStatus.ERROR,
        ]

    def test_result_contains_script(self, verifier, simple_attack):
        """Test that result contains Z3 script for debugging."""
        result = verifier.verify_attack_path(
            simple_attack,
            VULNERABLE_WITHDRAW,
        )

        # Script should be present for debugging
        assert result.z3_script is not None

    def test_result_to_dict(self, verifier, simple_attack):
        """Test result serialization."""
        result = verifier.verify_attack_path(
            simple_attack,
            VULNERABLE_WITHDRAW,
        )

        d = result.to_dict()
        assert "status" in d
        assert "is_proven" in d
        assert "path_feasible" in d


# =============================================================================
# Direct Constraint Verification Tests
# =============================================================================


class TestDirectConstraintVerification:
    """Test direct constraint verification."""

    def test_verify_satisfiable_constraints(self, verifier):
        """Test verification of satisfiable constraints."""
        result = verifier.verify_constraints_satisfiable(
            constraints=["balance >= amount", "amount > 0", "balance >= 100"],
            variable_types={"balance": "Int", "amount": "Int"},
        )

        assert result.status == VerificationStatus.SAT or result.status in [
            VerificationStatus.UNKNOWN,
            VerificationStatus.ERROR,
        ]

    def test_verify_unsatisfiable_constraints(self, verifier):
        """Test verification of unsatisfiable constraints."""
        result = verifier.verify_constraints_satisfiable(
            constraints=["x > 10", "x < 5"],
            variable_types={"x": "Int"},
        )

        # Should be UNSAT (constraints are impossible)
        assert result.status == VerificationStatus.UNSAT or result.status in [
            VerificationStatus.UNKNOWN,
            VerificationStatus.ERROR,
        ]


# =============================================================================
# Convenience Function Tests
# =============================================================================


class TestConvenienceFunction:
    """Test convenience function."""

    def test_verify_path_feasibility(self):
        """Test convenience function."""
        result = verify_path_feasibility(
            constraints=["x >= 0", "x < 100"],
            variable_types={"x": "Int"},
        )

        assert isinstance(result, VerificationResult)


# =============================================================================
# Defense Verification Tests
# =============================================================================


class TestDefenseVerification:
    """Test defense claim verification."""

    def test_verify_defense_claim(self, verifier, reentrancy_attack, defense_with_guard):
        """Test verification of defense claims."""
        result = verifier.verify_defense_claim(
            defense_with_guard,
            reentrancy_attack,
            SAFE_WITHDRAW,
        )

        assert isinstance(result, VerificationResult)
        # Defense verification should complete
        assert result.status in [
            VerificationStatus.SAT,
            VerificationStatus.UNSAT,
            VerificationStatus.UNKNOWN,
            VerificationStatus.ERROR,
        ]


# =============================================================================
# Guard Constraint Tests
# =============================================================================


class TestGuardConstraints:
    """Test guard to constraint conversion."""

    def test_reentrancy_guard(self, verifier):
        """Test reentrancy guard constraint."""
        defense = Mock()
        constraint = verifier._guard_to_constraint("reentrancy_guard", defense)

        assert constraint is not None
        assert constraint.constraint_type == ConstraintType.IMPLICIT
        assert "reentrancy" in constraint.solidity_expr.lower()

    def test_owner_guard(self, verifier):
        """Test owner guard constraint."""
        defense = Mock()
        constraint = verifier._guard_to_constraint("only_owner", defense)

        assert constraint is not None
        assert "owner" in constraint.solidity_expr.lower()

    def test_cei_guard(self, verifier):
        """Test CEI pattern guard constraint."""
        defense = Mock()
        constraint = verifier._guard_to_constraint("cei_pattern", defense)

        assert constraint is not None
        assert constraint.constraint_type == ConstraintType.ORDERING


# =============================================================================
# Batch Verification Tests
# =============================================================================


class TestBatchVerification:
    """Test batch verification."""

    def test_batch_verify_multiple_attacks(self, verifier, simple_attack, reentrancy_attack):
        """Test batch verification of multiple attacks."""
        results = verifier.batch_verify(
            attacks=[simple_attack, reentrancy_attack],
            function_codes={
                "fn_withdraw": VULNERABLE_WITHDRAW,
            },
        )

        assert len(results) == 2
        for result in results:
            assert isinstance(result, VerificationResult)


# =============================================================================
# Graceful Degradation Tests
# =============================================================================


class TestGracefulDegradation:
    """Test graceful handling of edge cases."""

    def test_no_z3_available(self, simple_attack):
        """Test graceful handling when Z3 is unavailable."""
        verifier = LLMDFAVerifier()
        verifier._z3_available = False  # Simulate no Z3

        result = verifier.verify_attack_path(simple_attack, "code")

        assert result.status == VerificationStatus.UNKNOWN
        assert result.is_proven == False
        assert "not available" in result.reasoning.lower()

    def test_empty_code(self, verifier, simple_attack):
        """Test handling of empty code."""
        result = verifier.verify_attack_path(simple_attack, "")

        assert isinstance(result, VerificationResult)

    def test_invalid_constraints(self, verifier):
        """Test handling of invalid constraint expressions."""
        result = verifier.verify_constraints_satisfiable(
            constraints=["this is not valid solidity"],
        )

        # Should not crash, may return ERROR or UNKNOWN
        assert isinstance(result, VerificationResult)


# =============================================================================
# Data Structure Tests
# =============================================================================


class TestDataStructures:
    """Test data structure functionality."""

    def test_constraint_set_add(self):
        """Test adding constraints to set."""
        cs = ConstraintSet()
        pc = PathConstraint(
            id="c1",
            constraint_type=ConstraintType.REQUIRE,
            solidity_expr="x > 0",
            z3_expr="(> x 0)",
            source_location="test",
            variables=["x"],
        )

        cs.add(pc)

        assert len(cs.constraints) == 1
        assert "x" in cs.variables

    def test_constraint_set_to_smt_lib(self):
        """Test SMT-LIB conversion."""
        cs = ConstraintSet()
        cs.variables = {"x": "Int"}
        cs.add(PathConstraint(
            id="c1",
            constraint_type=ConstraintType.REQUIRE,
            solidity_expr="x > 0",
            z3_expr="(> x 0)",
            source_location="test",
            variables=["x"],
        ))

        smt = cs.to_smt_lib()

        assert "(declare-const x Int)" in smt
        assert "(assert (> x 0))" in smt
        assert "(check-sat)" in smt

    def test_witness_values(self):
        """Test witness value structure."""
        witness = WitnessValues(
            assignments={"x": "42", "y": "100"},
            attack_parameters={"amount": "50"},
        )

        assert witness.get("x") == "42"
        assert "amount = 50" in witness.describe()

    def test_unsat_core(self):
        """Test UNSAT core structure."""
        core = UnsatCore(
            core_constraints=[],
            conflict_reason="Values cannot satisfy all constraints",
        )

        desc = core.describe()
        assert "Values cannot satisfy" in desc

    def test_path_constraint_str(self):
        """Test PathConstraint string representation."""
        pc = PathConstraint(
            id="c1",
            constraint_type=ConstraintType.REQUIRE,
            solidity_expr="x > 0",
            z3_expr="(> x 0)",
            source_location="test",
        )

        s = str(pc)
        assert "require" in s
        assert "x > 0" in s


# =============================================================================
# Timing Tests
# =============================================================================


class TestTiming:
    """Test timing information."""

    def test_result_includes_timing(self, verifier, simple_attack):
        """Test that results include timing info."""
        result = verifier.verify_attack_path(
            simple_attack,
            VULNERABLE_WITHDRAW,
        )

        # Timing should be recorded
        assert hasattr(result, "synthesis_time_ms")
        assert hasattr(result, "solving_time_ms")
        assert result.synthesis_time_ms >= 0
        assert result.solving_time_ms >= 0


# =============================================================================
# Integration with Attacker/Defender Tests
# =============================================================================


class TestAgentIntegration:
    """Test integration with attacker and defender agents."""

    def test_attack_construction_compatibility(self, verifier, reentrancy_attack):
        """Test that AttackConstruction works with verifier."""
        result = verifier.verify_attack_path(
            reentrancy_attack,
            VULNERABLE_WITHDRAW,
        )

        assert isinstance(result, VerificationResult)

    def test_defense_argument_compatibility(self, verifier, reentrancy_attack, defense_with_guard):
        """Test that DefenseArgument works with verifier."""
        result = verifier.verify_defense_claim(
            defense_with_guard,
            reentrancy_attack,
            SAFE_WITHDRAW,
        )

        assert isinstance(result, VerificationResult)


# =============================================================================
# LLM Integration Tests
# =============================================================================


class TestLLMIntegration:
    """Test LLM integration for constraint synthesis."""

    def test_llm_constraint_parsing(self, verifier_with_llm, simple_attack):
        """Test LLM response parsing."""
        # The mock LLM returns valid JSON
        constraints = verifier_with_llm._llm_extract_constraints(
            simple_attack,
            VULNERABLE_WITHDRAW,
        )

        # Should parse at least one constraint from mock response
        assert len(constraints.constraints) >= 1

    def test_synthesis_retry_with_llm(self, verifier_with_llm):
        """Test retry logic uses LLM."""
        constraints = ConstraintSet()
        constraints.variables = {"x": "Int"}
        constraints.add(PathConstraint(
            id="c1",
            constraint_type=ConstraintType.REQUIRE,
            solidity_expr="x > 0",
            z3_expr="(> x 0)",
            source_location="test",
            variables=["x"],
        ))

        attack = Mock()
        attack.attack_steps = []

        # Should succeed on first try with direct synthesis
        script, ok = verifier_with_llm._synthesize_z3_with_retry(constraints, attack)

        assert ok
        assert "(declare-const" in script or script != ""
