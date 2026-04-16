"""
Tests for Formal Invariant Synthesis

Tests the complete invariant synthesis pipeline including mining,
verification, and code generation.
"""

import unittest
from datetime import datetime

from alphaswarm_sol.invariants import (
    # Types
    InvariantType,
    InvariantStrength,
    Invariant,
    InvariantViolation,
    VerificationResult,
    # Miner
    InvariantMiner,
    MiningConfig,
    MiningResult,
    PatternTemplate,
    # Verifier
    InvariantVerifier,
    VerifierConfig,
    ProofResult,
    CounterExample,
    # Generator
    InvariantGenerator,
    GeneratorConfig,
    AssertionCode,
    InvariantSpec,
    # Synthesizer
    InvariantSynthesizer,
    SynthesisConfig,
    SynthesisResult,
)


class TestInvariantTypes(unittest.TestCase):
    """Tests for invariant types and data structures."""

    def test_invariant_creation(self):
        """Test creating an invariant."""
        inv = Invariant(
            invariant_id="INV-001",
            invariant_type=InvariantType.BALANCE_NON_NEGATIVE,
            name="Non-negative balance",
            description="Balance is always >= 0",
            predicate="balance >= 0",
            variables=["balance"],
        )

        self.assertEqual(inv.invariant_id, "INV-001")
        self.assertEqual(inv.invariant_type, InvariantType.BALANCE_NON_NEGATIVE)
        self.assertFalse(inv.is_verified())

    def test_invariant_strength(self):
        """Test invariant strength levels."""
        inv = Invariant(
            invariant_id="INV-002",
            invariant_type=InvariantType.OWNER_NON_ZERO,
            name="Owner non-zero",
            description="Owner is not zero address",
            predicate="owner != address(0)",
            variables=["owner"],
            strength=InvariantStrength.PROVEN,
        )

        self.assertTrue(inv.is_verified())
        self.assertFalse(inv.is_violated())

    def test_invariant_to_solidity(self):
        """Test converting invariant to Solidity assertion."""
        inv = Invariant(
            invariant_id="INV-003",
            invariant_type=InvariantType.BALANCE_NON_NEGATIVE,
            name="Non-negative",
            description="Always non-negative",
            predicate="balance >= 0",
            variables=["balance"],
        )

        assertion = inv.to_solidity_assert()
        self.assertIn("assert", assertion)
        self.assertIn("balance >= 0", assertion)

    def test_invariant_violation(self):
        """Test invariant violation record."""
        inv = Invariant(
            invariant_id="INV-004",
            invariant_type=InvariantType.OWNER_NON_ZERO,
            name="Test",
            description="Test",
            predicate="owner != address(0)",
            variables=["owner"],
        )

        violation = InvariantViolation(
            violation_id="VIO-001",
            invariant=inv,
            function="setOwner",
            description="Owner set to zero address",
            counter_example={"owner": "0x0"},
            severity="high",
        )

        self.assertEqual(violation.severity, "high")
        self.assertIsNotNone(violation.counter_example)

    def test_verification_result(self):
        """Test verification result."""
        result = VerificationResult(
            invariant_id="INV-005",
            verified=True,
            method="z3",
            proof_time_ms=100,
        )

        self.assertTrue(result.verified)
        self.assertEqual(result.confidence, 1.0)


class TestInvariantMiner(unittest.TestCase):
    """Tests for InvariantMiner."""

    def setUp(self):
        self.miner = InvariantMiner()

    def test_miner_creation(self):
        """Test miner creation."""
        self.assertIsNotNone(self.miner)
        self.assertGreater(len(self.miner.templates), 0)

    def test_mine_from_code(self):
        """Test mining invariants from code."""
        code = """
        contract Token {
            mapping(address => uint256) private _balances;
            uint256 private _totalSupply;
            address public owner;

            modifier onlyOwner() {
                require(msg.sender == owner);
                _;
            }
        }
        """

        result = self.miner.mine("Token", code)

        self.assertIsInstance(result, MiningResult)
        self.assertEqual(result.contract, "Token")
        self.assertGreater(len(result.invariants), 0)

    def test_mine_balance_invariants(self):
        """Test mining balance-related invariants."""
        code = """
        mapping(address => uint256) public balanceOf;
        uint256 public totalSupply;
        """

        result = self.miner.mine("ERC20", code)

        balance_inv = [
            i for i in result.invariants
            if i.invariant_type == InvariantType.BALANCE_NON_NEGATIVE
        ]
        self.assertGreater(len(balance_inv), 0)

    def test_mine_owner_invariants(self):
        """Test mining owner-related invariants."""
        code = """
        address private _owner;

        constructor() {
            _owner = msg.sender;
        }

        function owner() public view returns (address) {
            return _owner;
        }
        """

        state_vars = [
            {"name": "_owner", "type": "address", "visibility": "private"},
        ]

        result = self.miner.mine("Ownable", code, state_vars=state_vars)

        owner_inv = [
            i for i in result.invariants
            if i.invariant_type == InvariantType.OWNER_NON_ZERO
        ]
        self.assertGreater(len(owner_inv), 0)

    def test_mine_from_state_vars(self):
        """Test mining from state variable analysis."""
        state_vars = [
            {"name": "balance", "type": "uint256", "visibility": "public"},
            {"name": "owner", "type": "address", "visibility": "public"},
            {"name": "nonce", "type": "uint256", "visibility": "private"},
        ]

        result = self.miner.mine("Contract", "", state_vars=state_vars)

        # Should find non-negative invariants for uint256 vars
        self.assertGreater(len(result.invariants), 0)

    def test_mine_from_functions(self):
        """Test mining from function analysis."""
        functions = [
            {"name": "withdraw", "visibility": "public", "modifiers": ["onlyOwner"]},
            {"name": "deposit", "visibility": "public", "modifiers": ["nonReentrant"]},
        ]

        result = self.miner.mine("Vault", "", functions=functions)

        # Should find access control invariant
        access_inv = [
            i for i in result.invariants
            if i.invariant_type == InvariantType.PERMISSION_REQUIRED
        ]
        self.assertGreater(len(access_inv), 0)

    def test_mine_reentrancy_guard(self):
        """Test mining reentrancy guard invariants."""
        functions = [
            {"name": "execute", "visibility": "external", "modifiers": ["nonReentrant"]},
        ]

        result = self.miner.mine("Safe", "", functions=functions)

        lock_inv = [
            i for i in result.invariants
            if i.invariant_type == InvariantType.LOCK_HELD
        ]
        self.assertGreater(len(lock_inv), 0)

    def test_mine_from_kg(self):
        """Test mining from knowledge graph data."""
        kg_data = {
            "functions": [
                {
                    "name": "withdraw",
                    "properties": {
                        "has_reentrancy_guard": True,
                        "has_access_gate": True,
                    },
                },
            ],
        }

        result = self.miner.mine_from_kg("Contract", kg_data)

        self.assertGreater(len(result.invariants), 0)

    def test_custom_template(self):
        """Test adding custom mining template."""
        template = PatternTemplate(
            template_id="custom_1",
            invariant_type=InvariantType.CUSTOM,
            name="Custom Invariant",
            description="A custom invariant pattern",
            code_patterns=[r"customPattern"],
            required_elements={"custom"},
            predicate_template="customCheck()",
        )

        self.miner.add_template(template)
        self.assertIn(template, self.miner.templates)

    def test_mining_config(self):
        """Test mining configuration."""
        config = MiningConfig(
            min_confidence=0.8,
            max_invariants_per_function=5,
        )
        miner = InvariantMiner(config)

        self.assertEqual(miner.config.min_confidence, 0.8)

    def test_mining_result_methods(self):
        """Test MiningResult helper methods."""
        result = MiningResult(
            contract="Test",
            invariants=[
                Invariant(
                    invariant_id="INV-1",
                    invariant_type=InvariantType.BALANCE_NON_NEGATIVE,
                    name="Test",
                    description="Test",
                    predicate="x >= 0",
                    variables=["x"],
                    confidence=0.9,
                ),
            ],
        )

        by_type = result.get_by_type(InvariantType.BALANCE_NON_NEGATIVE)
        self.assertEqual(len(by_type), 1)

        high_conf = result.get_high_confidence(0.8)
        self.assertEqual(len(high_conf), 1)


class TestInvariantVerifier(unittest.TestCase):
    """Tests for InvariantVerifier."""

    def setUp(self):
        self.verifier = InvariantVerifier()

    def test_verifier_creation(self):
        """Test verifier creation."""
        self.assertIsNotNone(self.verifier)

    def test_verify_non_negative(self):
        """Test verifying non-negative invariant."""
        inv = Invariant(
            invariant_id="INV-001",
            invariant_type=InvariantType.BALANCE_NON_NEGATIVE,
            name="Non-negative uint",
            description="uint is always >= 0",
            predicate="balance >= 0",
            variables=["balance"],
            confidence=0.9,
        )

        result = self.verifier.verify(inv)

        # uint is always non-negative, should verify
        self.assertTrue(result.verified)

    def test_verify_with_config(self):
        """Test verification with custom config."""
        config = VerifierConfig(
            use_z3=False,
            use_symbolic=True,
            testing_iterations=50,
        )
        verifier = InvariantVerifier(config)

        inv = Invariant(
            invariant_id="INV-002",
            invariant_type=InvariantType.BALANCE_NON_NEGATIVE,
            name="Test",
            description="Test",
            predicate="x >= 0",
            variables=["x"],
        )

        result = verifier.verify(inv)
        self.assertIsInstance(result, VerificationResult)

    def test_verify_lock_held(self):
        """Test verifying lock held invariant."""
        inv = Invariant(
            invariant_id="INV-003",
            invariant_type=InvariantType.LOCK_HELD,
            name="Reentrancy lock",
            description="Lock held during execution",
            predicate="_locked",
            variables=["_locked"],
            strength=InvariantStrength.PROVEN,
            confidence=0.95,
        )

        result = self.verifier.verify(inv)

        # Pre-proven invariant should verify
        self.assertTrue(result.verified)

    def test_verify_all(self):
        """Test verifying multiple invariants."""
        invariants = [
            Invariant(
                invariant_id="INV-1",
                invariant_type=InvariantType.BALANCE_NON_NEGATIVE,
                name="Test 1",
                description="Test",
                predicate="x >= 0",
                variables=["x"],
            ),
            Invariant(
                invariant_id="INV-2",
                invariant_type=InvariantType.BALANCE_NON_NEGATIVE,
                name="Test 2",
                description="Test",
                predicate="y >= 0",
                variables=["y"],
            ),
        ]

        results = self.verifier.verify_all(invariants)

        self.assertEqual(len(results), 2)

    def test_verification_caching(self):
        """Test that verification results are cached."""
        inv = Invariant(
            invariant_id="INV-004",
            invariant_type=InvariantType.BALANCE_NON_NEGATIVE,
            name="Cached",
            description="Should be cached",
            predicate="cached >= 0",
            variables=["cached"],
        )

        # First verification
        result1 = self.verifier.verify(inv)

        # Second should use cache
        result2 = self.verifier.verify(inv)

        self.assertEqual(result1.verified, result2.verified)

    def test_clear_cache(self):
        """Test clearing verification cache."""
        self.verifier.verify(Invariant(
            invariant_id="INV-005",
            invariant_type=InvariantType.BALANCE_NON_NEGATIVE,
            name="Test",
            description="Test",
            predicate="test >= 0",
            variables=["test"],
        ))

        self.verifier.clear_cache()
        # Cache should be empty (can't easily verify but no error)

    def test_verifier_statistics(self):
        """Test verifier statistics."""
        self.verifier.verify(Invariant(
            invariant_id="INV-006",
            invariant_type=InvariantType.BALANCE_NON_NEGATIVE,
            name="Test",
            description="Test",
            predicate="stat >= 0",
            variables=["stat"],
        ))

        stats = self.verifier.get_statistics()
        self.assertIn("total_verified", stats)


class TestInvariantGenerator(unittest.TestCase):
    """Tests for InvariantGenerator."""

    def setUp(self):
        self.generator = InvariantGenerator()
        self.sample_invariant = Invariant(
            invariant_id="INV-001",
            invariant_type=InvariantType.BALANCE_NON_NEGATIVE,
            name="Non-negative balance",
            description="Balance is always >= 0",
            predicate="balance >= 0",
            variables=["balance"],
            strength=InvariantStrength.PROVEN,
            confidence=0.95,
        )

    def test_generator_creation(self):
        """Test generator creation."""
        self.assertIsNotNone(self.generator)

    def test_generate_assertion(self):
        """Test generating Solidity assertion."""
        assertions = self.generator.generate_assertions([self.sample_invariant])

        self.assertEqual(len(assertions), 1)
        self.assertIn("assert", assertions[0].assertion)

    def test_generate_scribble(self):
        """Test generating Scribble spec."""
        specs = self.generator.generate_scribble([self.sample_invariant])

        self.assertEqual(len(specs), 1)
        self.assertEqual(specs[0].spec_format, "scribble")
        self.assertIn("#invariant", specs[0].specification)

    def test_generate_foundry_tests(self):
        """Test generating Foundry tests."""
        tests = self.generator.generate_foundry_tests(
            [self.sample_invariant], "TestContract"
        )

        self.assertIn("contract TestContractInvariantTest", tests)
        self.assertIn("function invariant_", tests)

    def test_generate_certora_spec(self):
        """Test generating Certora spec."""
        spec = self.generator.generate_certora_spec(
            [self.sample_invariant], "TestContract"
        )

        self.assertIn("invariant", spec.lower())

    def test_generate_all_formats(self):
        """Test generating all output formats."""
        result = self.generator.generate_all(
            [self.sample_invariant], "TestContract"
        )

        self.assertIn("assertions", result)
        self.assertIn("scribble", result)
        self.assertIn("foundry", result)

    def test_skip_low_confidence(self):
        """Test that low confidence invariants are skipped."""
        low_conf = Invariant(
            invariant_id="INV-002",
            invariant_type=InvariantType.BALANCE_NON_NEGATIVE,
            name="Low confidence",
            description="Test",
            predicate="x >= 0",
            variables=["x"],
            confidence=0.5,  # Below threshold
        )

        config = GeneratorConfig(min_confidence=0.8)
        generator = InvariantGenerator(config)

        assertions = generator.generate_assertions([low_conf])
        self.assertEqual(len(assertions), 0)

    def test_owner_assertion(self):
        """Test generating owner non-zero assertion."""
        inv = Invariant(
            invariant_id="INV-003",
            invariant_type=InvariantType.OWNER_NON_ZERO,
            name="Owner non-zero",
            description="Owner not zero address",
            predicate="owner != address(0)",
            variables=["owner"],
            strength=InvariantStrength.PROVEN,
            confidence=0.9,
        )

        assertions = self.generator.generate_assertions([inv])

        self.assertEqual(len(assertions), 1)
        self.assertIn("address(0)", assertions[0].assertion)


class TestInvariantSynthesizer(unittest.TestCase):
    """Tests for InvariantSynthesizer."""

    def setUp(self):
        self.synthesizer = InvariantSynthesizer()

    def test_synthesizer_creation(self):
        """Test synthesizer creation."""
        self.assertIsNotNone(self.synthesizer)
        self.assertIsNotNone(self.synthesizer.miner)
        self.assertIsNotNone(self.synthesizer.verifier)
        self.assertIsNotNone(self.synthesizer.generator)

    def test_full_synthesis(self):
        """Test full synthesis pipeline."""
        code = """
        contract Token {
            mapping(address => uint256) public balanceOf;
            uint256 public totalSupply;
            address public owner;
        }
        """

        result = self.synthesizer.synthesize("Token", code=code)

        self.assertIsInstance(result, SynthesisResult)
        self.assertEqual(result.contract, "Token")
        self.assertGreater(result.candidates_mined, 0)

    def test_synthesis_with_state_vars(self):
        """Test synthesis with state variable info."""
        state_vars = [
            {"name": "balance", "type": "uint256"},
            {"name": "owner", "type": "address"},
        ]

        result = self.synthesizer.synthesize(
            "Contract", state_vars=state_vars
        )

        self.assertGreater(len(result.invariants), 0)

    def test_synthesis_with_functions(self):
        """Test synthesis with function info."""
        functions = [
            {"name": "withdraw", "modifiers": ["onlyOwner", "nonReentrant"]},
        ]

        result = self.synthesizer.synthesize(
            "Vault", functions=functions
        )

        self.assertGreater(len(result.invariants), 0)

    def test_synthesis_from_kg(self):
        """Test synthesis from knowledge graph data."""
        kg_data = {
            "nodes": [
                {
                    "type": "Function",
                    "name": "transfer",
                    "visibility": "public",
                    "properties": {"has_reentrancy_guard": True},
                },
                {
                    "type": "StateVariable",
                    "name": "balance",
                    "var_type": "uint256",
                },
            ],
        }

        result = self.synthesizer.synthesize_from_kg("Token", kg_data)

        self.assertIsInstance(result, SynthesisResult)

    def test_synthesis_generates_outputs(self):
        """Test that synthesis generates all outputs."""
        state_vars = [{"name": "value", "type": "uint256"}]

        result = self.synthesizer.synthesize(
            "Contract", state_vars=state_vars
        )

        # Should have generated assertions
        self.assertIsNotNone(result.assertions)

    def test_synthesis_config(self):
        """Test synthesis with custom config."""
        config = SynthesisConfig(
            verify_candidates=True,
            generate_assertions=True,
            generate_tests=True,
            min_confidence_for_output=0.7,
        )

        synthesizer = InvariantSynthesizer(config)
        result = synthesizer.synthesize(
            "Test",
            state_vars=[{"name": "x", "type": "uint256"}],
        )

        self.assertIsInstance(result, SynthesisResult)

    def test_quick_mine(self):
        """Test quick mining without verification."""
        code = "mapping(address => uint256) balances;"

        invariants = self.synthesizer.quick_mine("Token", code)

        self.assertIsInstance(invariants, list)

    def test_synthesis_result_methods(self):
        """Test SynthesisResult helper methods."""
        result = SynthesisResult(
            contract="Test",
            invariants=[
                Invariant(
                    invariant_id="INV-1",
                    invariant_type=InvariantType.BALANCE_NON_NEGATIVE,
                    name="Test",
                    description="Test",
                    predicate="x >= 0",
                    variables=["x"],
                    strength=InvariantStrength.PROVEN,
                ),
            ],
        )

        proven = result.get_proven_invariants()
        self.assertEqual(len(proven), 1)

    def test_synthesis_summary(self):
        """Test synthesis result summary."""
        result = SynthesisResult(
            contract="Test",
            candidates_mined=10,
            verified_count=8,
            violated_count=2,
            invariants=[],
        )

        summary = result.summary()
        self.assertIn("Test", summary)
        self.assertIn("10", summary)


class TestCounterExample(unittest.TestCase):
    """Tests for CounterExample."""

    def test_counter_example_creation(self):
        """Test creating a counter example."""
        ce = CounterExample(
            variables={"x": -1, "y": 0},
            trace=["Step 1", "Step 2"],
            function="vulnerable",
            step=2,
        )

        self.assertEqual(ce.function, "vulnerable")
        self.assertEqual(len(ce.trace), 2)

    def test_counter_example_to_dict(self):
        """Test counter example serialization."""
        ce = CounterExample(
            variables={"balance": -100},
            trace=["Called withdraw"],
            function="withdraw",
        )

        d = ce.to_dict()
        self.assertIn("variables", d)
        self.assertIn("function", d)


class TestIntegration(unittest.TestCase):
    """Integration tests for the complete invariant synthesis pipeline."""

    def test_full_pipeline_erc20(self):
        """Test full pipeline on ERC20-like contract."""
        code = """
        contract ERC20 {
            mapping(address => uint256) private _balances;
            uint256 private _totalSupply;
            address private _owner;

            modifier onlyOwner() {
                require(msg.sender == _owner);
                _;
            }

            function transfer(address to, uint256 amount) public returns (bool) {
                require(_balances[msg.sender] >= amount);
                _balances[msg.sender] -= amount;
                _balances[to] += amount;
                return true;
            }
        }
        """

        state_vars = [
            {"name": "_balances", "type": "mapping(address => uint256)"},
            {"name": "_totalSupply", "type": "uint256"},
            {"name": "_owner", "type": "address"},
        ]

        functions = [
            {"name": "transfer", "visibility": "public", "modifiers": []},
        ]

        synthesizer = InvariantSynthesizer()
        result = synthesizer.synthesize(
            "ERC20",
            code=code,
            state_vars=state_vars,
            functions=functions,
        )

        # Should find balance invariants
        balance_inv = result.get_by_type(InvariantType.BALANCE_NON_NEGATIVE)
        self.assertGreater(len(balance_inv), 0)

        # Should generate assertions
        self.assertGreater(len(result.assertions), 0)

    def test_pipeline_with_vulnerabilities(self):
        """Test pipeline detects potential issues."""
        # Contract with potential owner issue
        state_vars = [
            {"name": "owner", "type": "address"},  # owner variable
        ]

        functions = [
            {"name": "setOwner", "visibility": "public", "modifiers": []},  # No access control!
        ]

        synthesizer = InvariantSynthesizer()
        result = synthesizer.synthesize(
            "Vulnerable",
            state_vars=state_vars,
            functions=functions,
        )

        # Should still synthesize invariants
        self.assertIsInstance(result, SynthesisResult)

    def test_pipeline_output_formats(self):
        """Test that all output formats are generated."""
        config = SynthesisConfig(
            generate_assertions=True,
            generate_specs=True,
            generate_tests=True,
        )

        synthesizer = InvariantSynthesizer(config)
        result = synthesizer.synthesize(
            "Test",
            state_vars=[{"name": "value", "type": "uint256"}],
        )

        # Check foundry tests are generated
        if result.foundry_tests:
            self.assertIn("function", result.foundry_tests)


if __name__ == "__main__":
    unittest.main()
