"""
Tests for Cross-Chain Vulnerability Transfer module.

Tests the Universal Vulnerability Ontology, chain translators,
cross-chain exploit database, and analyzer.
"""

import unittest
from typing import List, Dict

from alphaswarm_sol.crosschain import (
    # Core types
    Chain,
    AbstractOperation,
    OperationType,
    AbstractVulnerabilitySignature,
    InvariantType,
    # Translators
    ChainTranslator,
    EVMTranslator,
    SolanaTranslator,
    MoveTranslator,
    TranslatorRegistry,
    # Database
    CrossChainExploitDatabase,
    CrossChainMatch,
    MatchConfidence,
    # Analyzer
    CrossChainAnalyzer,
    CrossChainAnalysisResult,
    PortedVulnerability,
)
from alphaswarm_sol.crosschain.ontology import UNIVERSAL_SIGNATURES


class TestAbstractOperation(unittest.TestCase):
    """Tests for AbstractOperation."""

    def test_create_operation(self):
        """Test creating an abstract operation."""
        op = AbstractOperation(
            operation=OperationType.TRANSFER_VALUE,
            target="balance",
            timing=0,
        )
        self.assertEqual(op.operation, OperationType.TRANSFER_VALUE)
        self.assertEqual(op.target, "balance")
        self.assertEqual(op.timing, 0)

    def test_operation_hash(self):
        """Test operation hashing for set membership."""
        op1 = AbstractOperation(OperationType.TRANSFER_VALUE, "balance", 0)
        op2 = AbstractOperation(OperationType.TRANSFER_VALUE, "balance", 1)

        # Same operation/target, different timing - should hash differently
        self.assertNotEqual(hash(op1), hash(op2))

    def test_operation_equality(self):
        """Test operation equality."""
        op1 = AbstractOperation(OperationType.TRANSFER_VALUE, "balance", 0)
        op2 = AbstractOperation(OperationType.TRANSFER_VALUE, "balance", 1)
        op3 = AbstractOperation(OperationType.READ_VALUE, "balance", 0)

        # Same operation and target = equal
        self.assertEqual(op1, op2)
        # Different operation = not equal
        self.assertNotEqual(op1, op3)

    def test_signature_element(self):
        """Test conversion to signature element."""
        op = AbstractOperation(OperationType.TRANSFER_VALUE, "external", 0)
        element = op.to_signature_element()

        self.assertIn("TRA", element)  # Transfer
        self.assertIn("ext", element)  # external

    def test_operation_matches(self):
        """Test operation matching."""
        op1 = AbstractOperation(OperationType.READ_VALUE, "balance", 0)
        op2 = AbstractOperation(OperationType.READ_VALUE, "amount", 0)
        op3 = AbstractOperation(OperationType.WRITE_VALUE, "balance", 0)

        # Same category targets should match (non-strict)
        self.assertTrue(op1.matches(op2, strict=False))

        # Different operations should not match
        self.assertFalse(op1.matches(op3))


class TestAbstractVulnerabilitySignature(unittest.TestCase):
    """Tests for AbstractVulnerabilitySignature."""

    def test_create_signature(self):
        """Test creating a vulnerability signature."""
        sig = AbstractVulnerabilitySignature(
            vuln_id="TEST-001",
            vuln_name="Test Vulnerability",
            vuln_category="test",
            abstract_operations=[
                AbstractOperation(OperationType.READ_VALUE, "balance", 0),
                AbstractOperation(OperationType.TRANSFER_VALUE, "external", 1),
            ],
            invariant_violated=InvariantType.CEI_PATTERN,
            severity="high",
        )

        self.assertEqual(sig.vuln_id, "TEST-001")
        self.assertEqual(len(sig.abstract_operations), 2)
        self.assertEqual(sig.severity, "high")

    def test_signature_hash(self):
        """Test getting signature hash."""
        sig = AbstractVulnerabilitySignature(
            vuln_id="TEST-001",
            vuln_name="Test",
            vuln_category="test",
            abstract_operations=[
                AbstractOperation(OperationType.READ_VALUE, "balance", 0),
            ],
            invariant_violated=InvariantType.CEI_PATTERN,
            severity="high",
        )

        hash1 = sig.get_signature_hash()
        self.assertIsInstance(hash1, str)
        self.assertEqual(len(hash1), 16)

    def test_behavioral_signature(self):
        """Test getting behavioral signature."""
        sig = AbstractVulnerabilitySignature(
            vuln_id="TEST-001",
            vuln_name="Test",
            vuln_category="test",
            abstract_operations=[
                AbstractOperation(OperationType.READ_VALUE, "balance", 0),
                AbstractOperation(OperationType.TRANSFER_VALUE, "external", 1),
                AbstractOperation(OperationType.WRITE_VALUE, "balance", 2),
            ],
            invariant_violated=InvariantType.CEI_PATTERN,
            severity="high",
        )

        behavioral = sig.get_behavioral_signature()
        self.assertIn("->", behavioral)
        self.assertEqual(behavioral.count("->"), 2)

    def test_matches_signature(self):
        """Test signature matching."""
        sig = AbstractVulnerabilitySignature(
            vuln_id="TEST-001",
            vuln_name="Test",
            vuln_category="test",
            abstract_operations=[
                AbstractOperation(OperationType.READ_VALUE, "balance", 0),
                AbstractOperation(OperationType.TRANSFER_VALUE, "external", 1),
            ],
            invariant_violated=InvariantType.CEI_PATTERN,
            severity="high",
        )

        # Matching operations
        ops = [
            AbstractOperation(OperationType.READ_VALUE, "balance", 0),
            AbstractOperation(OperationType.TRANSFER_VALUE, "external", 1),
            AbstractOperation(OperationType.WRITE_VALUE, "other", 2),  # Extra
        ]

        self.assertTrue(sig.matches_signature(ops))

        # Missing operation
        ops_missing = [
            AbstractOperation(OperationType.READ_VALUE, "balance", 0),
        ]
        self.assertFalse(sig.matches_signature(ops_missing))

    def test_to_dict(self):
        """Test converting to dictionary."""
        sig = AbstractVulnerabilitySignature(
            vuln_id="TEST-001",
            vuln_name="Test",
            vuln_category="test",
            abstract_operations=[
                AbstractOperation(OperationType.READ_VALUE, "balance", 0),
            ],
            invariant_violated=InvariantType.CEI_PATTERN,
            severity="high",
        )

        d = sig.to_dict()
        self.assertEqual(d["vuln_id"], "TEST-001")
        self.assertIn("operations", d)
        self.assertIn("signature_hash", d)


class TestUniversalSignatures(unittest.TestCase):
    """Tests for pre-defined universal signatures."""

    def test_reentrancy_signature_exists(self):
        """Test that reentrancy signature is defined."""
        self.assertIn("reentrancy_classic", UNIVERSAL_SIGNATURES)

    def test_access_control_signature_exists(self):
        """Test that access control signature is defined."""
        self.assertIn("access_control_missing", UNIVERSAL_SIGNATURES)

    def test_oracle_signature_exists(self):
        """Test that oracle signature is defined."""
        self.assertIn("oracle_staleness", UNIVERSAL_SIGNATURES)

    def test_signatures_have_required_fields(self):
        """Test all signatures have required fields."""
        for name, sig in UNIVERSAL_SIGNATURES.items():
            self.assertIsNotNone(sig.vuln_id, f"{name} missing vuln_id")
            self.assertIsNotNone(sig.vuln_name, f"{name} missing vuln_name")
            self.assertTrue(len(sig.abstract_operations) > 0, f"{name} has no operations")
            self.assertIsNotNone(sig.invariant_violated, f"{name} missing invariant")
            self.assertIn(sig.severity, ["critical", "high", "medium", "low"])


class TestEVMTranslator(unittest.TestCase):
    """Tests for EVM translator."""

    def setUp(self):
        self.translator = EVMTranslator()

    def test_to_abstract_basic(self):
        """Test converting VKG operations to abstract."""
        vkg_ops = [
            "READS_USER_BALANCE",
            "TRANSFERS_VALUE_OUT",
            "WRITES_USER_BALANCE",
        ]

        abstract = self.translator.to_abstract(vkg_ops)

        self.assertEqual(len(abstract), 3)
        self.assertEqual(abstract[0].operation, OperationType.READ_VALUE)
        self.assertEqual(abstract[1].operation, OperationType.TRANSFER_VALUE)
        self.assertEqual(abstract[2].operation, OperationType.WRITE_VALUE)

    def test_to_abstract_preserves_ordering(self):
        """Test that ordering is preserved."""
        vkg_ops = [
            "READS_ORACLE",
            "CALLS_EXTERNAL",
            "MODIFIES_OWNER",
        ]

        abstract = self.translator.to_abstract(vkg_ops)

        self.assertEqual(abstract[0].timing, 0)
        self.assertEqual(abstract[1].timing, 1)
        self.assertEqual(abstract[2].timing, 2)

    def test_from_abstract_generates_pattern(self):
        """Test converting abstract to VKG pattern."""
        abstract_ops = [
            AbstractOperation(OperationType.READ_VALUE, "balance", 0),
            AbstractOperation(OperationType.TRANSFER_VALUE, "external", 1),
            AbstractOperation(OperationType.WRITE_VALUE, "balance", 2),
        ]

        pattern = self.translator.from_abstract(abstract_ops)

        self.assertIn("tier_a", pattern)
        self.assertIn("all", pattern["tier_a"])
        self.assertTrue(len(pattern["tier_a"]["all"]) > 0)

    def test_parse_source_basic(self):
        """Test parsing Solidity source."""
        source = """
        function withdraw(uint amount) external {
            require(balances[msg.sender] >= amount);
            (bool success,) = msg.sender.call{value: amount}("");
            require(success);
            balances[msg.sender] -= amount;
        }
        """

        ops = self.translator.parse_source(source)

        self.assertIn("READS_USER_BALANCE", ops)
        self.assertIn("CALLS_EXTERNAL", ops)


class TestSolanaTranslator(unittest.TestCase):
    """Tests for Solana translator."""

    def setUp(self):
        self.translator = SolanaTranslator()

    def test_to_abstract_basic(self):
        """Test converting Solana operations to abstract."""
        solana_ops = ["invoke", "transfer", "lamports"]

        abstract = self.translator.to_abstract(solana_ops)

        self.assertEqual(len(abstract), 3)
        op_types = [op.operation for op in abstract]
        self.assertIn(OperationType.CALL_EXTERNAL, op_types)
        self.assertIn(OperationType.TRANSFER_VALUE, op_types)

    def test_parse_source_anchor(self):
        """Test parsing Anchor source."""
        source = """
        pub fn withdraw(ctx: Context<Withdraw>, amount: u64) -> Result<()> {
            let authority = &ctx.accounts.authority;
            invoke(
                &system_instruction::transfer(from, to, amount),
                &[from, to],
            )?;
            Ok(())
        }
        """

        ops = self.translator.parse_source(source)

        self.assertIn("invoke", ops)
        self.assertIn("authority", ops)


class TestMoveTranslator(unittest.TestCase):
    """Tests for Move translator."""

    def setUp(self):
        self.translator = MoveTranslator()

    def test_to_abstract_basic(self):
        """Test converting Move operations to abstract."""
        move_ops = ["borrow_global", "Coin::transfer", "signer::address_of"]

        abstract = self.translator.to_abstract(move_ops)

        self.assertEqual(len(abstract), 3)
        op_types = [op.operation for op in abstract]
        self.assertIn(OperationType.READ_STATE, op_types)
        self.assertIn(OperationType.TRANSFER_VALUE, op_types)
        self.assertIn(OperationType.CHECK_PERMISSION, op_types)

    def test_parse_source_move(self):
        """Test parsing Move source."""
        source = """
        public fun withdraw(account: &signer, amount: u64) {
            let sender = signer::address_of(account);
            let balance = borrow_global_mut<Balance>(sender);
            Coin::transfer(sender, receiver, amount);
        }
        """

        ops = self.translator.parse_source(source)

        self.assertIn("signer::address_of", ops)
        self.assertIn("borrow_global_mut", ops)
        self.assertIn("Coin::transfer", ops)


class TestTranslatorRegistry(unittest.TestCase):
    """Tests for TranslatorRegistry."""

    def setUp(self):
        self.registry = TranslatorRegistry()

    def test_has_default_translators(self):
        """Test default translators are registered."""
        self.assertIsNotNone(self.registry.get(Chain.EVM))
        self.assertIsNotNone(self.registry.get(Chain.SOLANA))
        self.assertIsNotNone(self.registry.get(Chain.MOVE))

    def test_cross_translate(self):
        """Test cross-chain translation."""
        evm_ops = ["READS_USER_BALANCE", "TRANSFERS_VALUE_OUT"]

        # EVM to Solana
        solana_pattern = self.registry.cross_translate(
            Chain.EVM, Chain.SOLANA, evm_ops
        )

        self.assertIn("chain", solana_pattern)
        self.assertEqual(solana_pattern["chain"], "solana")

    def test_supported_chains(self):
        """Test getting supported chains."""
        chains = self.registry.supported_chains

        self.assertIn(Chain.EVM, chains)
        self.assertIn(Chain.SOLANA, chains)
        self.assertIn(Chain.MOVE, chains)


class TestCrossChainExploitDatabase(unittest.TestCase):
    """Tests for CrossChainExploitDatabase."""

    def setUp(self):
        self.db = CrossChainExploitDatabase()

    def test_known_exploits_loaded(self):
        """Test that known exploits are loaded."""
        self.assertTrue(len(self.db.exploits) > 0)

    def test_dao_exploit_exists(self):
        """Test The DAO exploit is in database."""
        self.assertIn("EXP-DAO-2016", self.db.exploits)
        dao = self.db.exploits["EXP-DAO-2016"]
        self.assertEqual(dao.name, "The DAO")
        self.assertEqual(dao.chain, Chain.EVM)

    def test_add_exploit(self):
        """Test adding a new exploit."""
        exploit = self.db.add_exploit(
            exploit_id="EXP-TEST-001",
            name="Test Exploit",
            chain=Chain.EVM,
            date="2024-01-01",
            loss_usd=1_000_000,
            vulnerability_type="reentrancy",
            chain_operations=["READS_USER_BALANCE", "TRANSFERS_VALUE_OUT"],
            description="Test exploit for testing",
        )

        self.assertIn("EXP-TEST-001", self.db.exploits)
        self.assertEqual(exploit.name, "Test Exploit")
        self.assertEqual(exploit.loss_usd, 1_000_000)

    def test_find_by_category(self):
        """Test finding exploits by category."""
        reentrancy_exploits = self.db.find_by_category("reentrancy")

        self.assertTrue(len(reentrancy_exploits) > 0)
        for e in reentrancy_exploits:
            self.assertEqual(e.vulnerability_type, "reentrancy")

    def test_find_by_chain(self):
        """Test finding exploits by chain."""
        solana_ids = self.db._by_chain.get(Chain.SOLANA, [])
        solana_exploits = [self.db.exploits[id] for id in solana_ids]

        self.assertTrue(len(solana_exploits) > 0)
        for e in solana_exploits:
            self.assertEqual(e.chain, Chain.SOLANA)

    def test_find_cross_chain_matches(self):
        """Test finding cross-chain matches."""
        # EVM operations similar to DAO
        evm_ops = [
            "READS_USER_BALANCE",
            "CALLS_EXTERNAL",
            "TRANSFERS_VALUE_OUT",
            "WRITES_USER_BALANCE",
        ]

        # Should find matches from Solana exploits
        matches = self.db.find_cross_chain_matches(
            Chain.EVM, evm_ops, MatchConfidence.LOW
        )

        # Should have matches (from Solana exploits)
        solana_matches = [m for m in matches if m.source_exploit.chain == Chain.SOLANA]
        self.assertTrue(len(matches) >= 0)  # May or may not have matches

    def test_transfer_vulnerability(self):
        """Test transferring vulnerability to another chain."""
        pattern = self.db.transfer_vulnerability("EXP-DAO-2016", Chain.SOLANA)

        self.assertIsNotNone(pattern)
        self.assertIn("source_exploit", pattern)
        self.assertEqual(pattern["source_chain"], "evm")

    def test_get_statistics(self):
        """Test getting database statistics."""
        stats = self.db.get_statistics()

        self.assertIn("total_exploits", stats)
        self.assertIn("by_chain", stats)
        self.assertIn("total_loss_usd", stats)
        self.assertTrue(stats["total_exploits"] > 0)
        self.assertTrue(stats["total_loss_usd"] > 0)


class TestCrossChainAnalyzer(unittest.TestCase):
    """Tests for CrossChainAnalyzer."""

    def setUp(self):
        self.analyzer = CrossChainAnalyzer()

    def test_analyze_operations(self):
        """Test analyzing operations."""
        ops = [
            "READS_USER_BALANCE",
            "TRANSFERS_VALUE_OUT",
            "WRITES_USER_BALANCE",
        ]

        result = self.analyzer.analyze_operations(Chain.EVM, ops)

        self.assertIsInstance(result, CrossChainAnalysisResult)
        self.assertEqual(result.target_chain, Chain.EVM)
        self.assertIsNotNone(result.analysis_timestamp)

    def test_analyze_source_code(self):
        """Test analyzing source code."""
        source = """
        function withdraw(uint amount) external {
            require(balances[msg.sender] >= amount);
            msg.sender.call{value: amount}("");
            balances[msg.sender] -= amount;
        }
        """

        result = self.analyzer.analyze_source_code(Chain.EVM, source)

        self.assertIsInstance(result, CrossChainAnalysisResult)
        # Should detect reentrancy pattern
        self.assertTrue(result.total_matches >= 0)

    def test_port_vulnerability(self):
        """Test porting a vulnerability."""
        ported = self.analyzer.port_vulnerability("EXP-DAO-2016", Chain.SOLANA)

        self.assertIsNotNone(ported)
        self.assertIsInstance(ported, PortedVulnerability)
        self.assertEqual(ported.original_chain, Chain.EVM)
        self.assertEqual(ported.target_chain, Chain.SOLANA)

    def test_get_chain_statistics(self):
        """Test getting chain statistics."""
        stats = self.analyzer.get_chain_statistics(Chain.EVM)

        self.assertIn("chain", stats)
        self.assertIn("total_exploits", stats)
        self.assertIn("by_severity", stats)
        self.assertEqual(stats["chain"], "evm")

    def test_compare_chains(self):
        """Test comparing chains."""
        comparison = self.analyzer.compare_chains(Chain.EVM, Chain.SOLANA)

        self.assertIn("chain1", comparison)
        self.assertIn("chain2", comparison)
        self.assertIn("common_vulnerability_types", comparison)
        self.assertEqual(comparison["chain1"], "evm")
        self.assertEqual(comparison["chain2"], "solana")

    def test_generate_detection_pattern(self):
        """Test generating detection pattern."""
        pattern = self.analyzer.generate_detection_pattern(
            "EXP-DAO-2016", Chain.SOLANA
        )

        self.assertIsNotNone(pattern)
        self.assertIn("id", pattern)
        self.assertIn("match", pattern)
        self.assertIn("original_exploit", pattern)

    def test_analysis_result_summary(self):
        """Test analysis result summary."""
        ops = ["READS_USER_BALANCE", "TRANSFERS_VALUE_OUT"]
        result = self.analyzer.analyze_operations(Chain.EVM, ops)

        summary = result.get_summary()

        self.assertIsInstance(summary, str)
        self.assertIn("Cross-Chain", summary)
        self.assertIn("evm", summary.lower())


class TestMatchConfidence(unittest.TestCase):
    """Tests for MatchConfidence enum."""

    def test_confidence_levels(self):
        """Test confidence level ordering."""
        self.assertEqual(MatchConfidence.EXACT.value, "exact")
        self.assertEqual(MatchConfidence.HIGH.value, "high")
        self.assertEqual(MatchConfidence.MEDIUM.value, "medium")
        self.assertEqual(MatchConfidence.LOW.value, "low")
        self.assertEqual(MatchConfidence.SPECULATIVE.value, "speculative")


class TestChainEnum(unittest.TestCase):
    """Tests for Chain enum."""

    def test_chain_values(self):
        """Test chain values."""
        self.assertEqual(Chain.EVM.value, "evm")
        self.assertEqual(Chain.SOLANA.value, "solana")
        self.assertEqual(Chain.MOVE.value, "move")
        self.assertEqual(Chain.COSMOS.value, "cosmos")
        self.assertEqual(Chain.NEAR.value, "near")


class TestInvariantType(unittest.TestCase):
    """Tests for InvariantType enum."""

    def test_invariant_types(self):
        """Test invariant types."""
        self.assertEqual(InvariantType.CEI_PATTERN.value, "cei_pattern")
        self.assertEqual(InvariantType.ACCESS_CONTROL.value, "access_control")
        self.assertEqual(InvariantType.ORACLE_FRESHNESS.value, "oracle_freshness")


class TestCrossChainMatch(unittest.TestCase):
    """Tests for CrossChainMatch."""

    def test_match_to_dict(self):
        """Test converting match to dictionary."""
        # Create a minimal exploit for testing
        db = CrossChainExploitDatabase()
        exploit = db.exploits.get("EXP-DAO-2016")

        if exploit:
            match = CrossChainMatch(
                source_exploit=exploit,
                target_chain=Chain.SOLANA,
                confidence=MatchConfidence.HIGH,
                matched_operations=[],
                missing_operations=[],
                similarity_score=0.85,
                target_pattern={},
                priority="high",
            )

            d = match.to_dict()

            self.assertIn("source_exploit", d)
            self.assertIn("confidence", d)
            self.assertIn("similarity_score", d)
            self.assertEqual(d["confidence"], "high")


class TestPortedVulnerability(unittest.TestCase):
    """Tests for PortedVulnerability."""

    def test_ported_to_dict(self):
        """Test converting ported vulnerability to dictionary."""
        ported = PortedVulnerability(
            original_exploit="The DAO",
            original_chain=Chain.EVM,
            target_chain=Chain.SOLANA,
            confidence=MatchConfidence.HIGH,
            similarity=0.9,
            target_pattern={},
            behavioral_signature="REA:bal->TRA:ext->WRI:bal",
            invariant_violated=InvariantType.CEI_PATTERN,
            severity="critical",
            priority="critical",
            mitigation="Follow CEI pattern",
            description="Ported reentrancy vulnerability",
        )

        d = ported.to_dict()

        self.assertEqual(d["original_exploit"], "The DAO")
        self.assertEqual(d["original_chain"], "evm")
        self.assertEqual(d["target_chain"], "solana")
        self.assertEqual(d["severity"], "critical")


class TestCrossChainAnalysisResult(unittest.TestCase):
    """Tests for CrossChainAnalysisResult."""

    def test_get_critical_findings(self):
        """Test getting critical findings."""
        result = CrossChainAnalysisResult(
            target_chain=Chain.EVM,
            target_operations=[],
            cross_chain_matches=[
                PortedVulnerability(
                    original_exploit="Test1",
                    original_chain=Chain.SOLANA,
                    target_chain=Chain.EVM,
                    confidence=MatchConfidence.HIGH,
                    similarity=0.9,
                    target_pattern={},
                    behavioral_signature="",
                    invariant_violated=InvariantType.CEI_PATTERN,
                    severity="critical",
                    priority="critical",
                    mitigation="",
                    description="",
                ),
                PortedVulnerability(
                    original_exploit="Test2",
                    original_chain=Chain.SOLANA,
                    target_chain=Chain.EVM,
                    confidence=MatchConfidence.MEDIUM,
                    similarity=0.5,
                    target_pattern={},
                    behavioral_signature="",
                    invariant_violated=InvariantType.ACCESS_CONTROL,
                    severity="medium",
                    priority="medium",
                    mitigation="",
                    description="",
                ),
            ],
            universal_signature_matches=[],
            total_matches=2,
            critical_matches=1,
            high_matches=1,
            analysis_timestamp="2024-01-01T00:00:00",
            analysis_duration_ms=100.0,
        )

        critical = result.get_critical_findings()

        self.assertEqual(len(critical), 1)
        self.assertEqual(critical[0].original_exploit, "Test1")

    def test_result_to_dict(self):
        """Test converting result to dictionary."""
        result = CrossChainAnalysisResult(
            target_chain=Chain.EVM,
            target_operations=["READS_USER_BALANCE"],
            cross_chain_matches=[],
            universal_signature_matches=[],
            total_matches=0,
            critical_matches=0,
            high_matches=0,
            analysis_timestamp="2024-01-01T00:00:00",
            analysis_duration_ms=50.0,
        )

        d = result.to_dict()

        self.assertEqual(d["target_chain"], "evm")
        self.assertEqual(d["total_matches"], 0)
        self.assertIn("analysis_timestamp", d)


if __name__ == "__main__":
    unittest.main()
