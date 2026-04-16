"""
Phase 4 Task 1: Project Profiler Tests

Tests project profiling, similarity matching, and protocol classification.
"""

import unittest
import math
from unittest.mock import Mock, MagicMock

from alphaswarm_sol.transfer import (
    ProjectProfile,
    ProjectProfiler,
    ProjectDatabase,
)
from alphaswarm_sol.kg.schema import Node, KnowledgeGraph


class TestProjectProfile(unittest.TestCase):
    """Test ProjectProfile dataclass and similarity calculation."""

    def test_profile_creation(self):
        """Test creating a project profile."""
        profile = ProjectProfile(
            project_id="test_project",
            name="Test Project",
            is_upgradeable=True,
            proxy_pattern="transparent",
            uses_oracles=True,
            protocol_type="dex",
            primitives_used=["amm", "liquidity_pool"],
            num_contracts=5,
            num_functions=50,
            operation_histogram={"TRANSFERS_VALUE_OUT": 20, "WRITES_USER_BALANCE": 15},
        )

        self.assertEqual(profile.project_id, "test_project")
        self.assertEqual(profile.name, "Test Project")
        self.assertTrue(profile.is_upgradeable)
        self.assertEqual(profile.proxy_pattern, "transparent")
        self.assertTrue(profile.uses_oracles)
        self.assertEqual(profile.protocol_type, "dex")
        self.assertEqual(len(profile.primitives_used), 2)

    def test_similarity_identical(self):
        """Test similarity between identical profiles."""
        profile1 = ProjectProfile(
            project_id="p1",
            name="P1",
            is_upgradeable=False,
            protocol_type="dex",
            num_contracts=1,
            num_functions=1,
            embedding=[0.5, 0.5, 0.7071],  # Normalized
        )

        profile2 = ProjectProfile(
            project_id="p2",
            name="P2",
            is_upgradeable=False,
            protocol_type="dex",
            num_contracts=1,
            num_functions=1,
            embedding=[0.5, 0.5, 0.7071],  # Same
        )

        similarity = profile1.similarity_to(profile2)
        self.assertAlmostEqual(similarity, 1.0, places=4)

    def test_similarity_orthogonal(self):
        """Test similarity between orthogonal profiles."""
        profile1 = ProjectProfile(
            project_id="p1",
            name="P1",
            is_upgradeable=False,
            protocol_type="dex",
            num_contracts=1,
            num_functions=1,
            embedding=[1.0, 0.0, 0.0],
        )

        profile2 = ProjectProfile(
            project_id="p2",
            name="P2",
            is_upgradeable=False,
            protocol_type="lending",
            num_contracts=1,
            num_functions=1,
            embedding=[0.0, 1.0, 0.0],
        )

        similarity = profile1.similarity_to(profile2)
        self.assertAlmostEqual(similarity, 0.0, places=4)

    def test_similarity_no_embedding(self):
        """Test similarity when embeddings are missing."""
        profile1 = ProjectProfile(
            project_id="p1",
            name="P1",
            is_upgradeable=False,
            protocol_type="dex",
            num_contracts=1,
            num_functions=1,
        )

        profile2 = ProjectProfile(
            project_id="p2",
            name="P2",
            is_upgradeable=False,
            protocol_type="dex",
            num_contracts=1,
            num_functions=1,
        )

        similarity = profile1.similarity_to(profile2)
        self.assertEqual(similarity, 0.0)


class TestProjectProfiler(unittest.TestCase):
    """Test ProjectProfiler creation and classification."""

    def setUp(self):
        """Set up profiler instance."""
        self.profiler = ProjectProfiler()

    def _create_mock_kg(
        self,
        contracts_data: list,
        functions_data: list,
        state_vars: int = 0,
    ) -> KnowledgeGraph:
        """Helper to create mock KG."""
        kg = Mock(spec=KnowledgeGraph)

        # Create contract nodes
        contracts = []
        for i, data in enumerate(contracts_data):
            contract = Mock(spec=Node)
            contract.type = "Contract"
            contract.label = data.get("label", f"Contract{i}")
            contract.properties = data.get("properties", {})
            contracts.append(contract)

        # Create function nodes
        functions = []
        for i, data in enumerate(functions_data):
            fn = Mock(spec=Node)
            fn.type = "Function"
            fn.label = data.get("label", f"function{i}")
            fn.properties = data.get("properties", {})
            functions.append(fn)

        # Create state variable nodes
        state_nodes = []
        for i in range(state_vars):
            var = Mock(spec=Node)
            var.type = "StateVariable"
            var.label = f"var{i}"
            var.properties = {}
            state_nodes.append(var)

        # Combine all nodes
        all_nodes = contracts + functions + state_nodes
        kg.nodes = {str(i): node for i, node in enumerate(all_nodes)}

        kg.metadata = {"target": "/path/to/test_project.sol"}

        return kg

    def test_basic_profiling(self):
        """Test basic project profiling."""
        kg = self._create_mock_kg(
            contracts_data=[
                {"label": "Token", "properties": {"is_upgradeable": False}},
            ],
            functions_data=[
                {
                    "label": "transfer",
                    "properties": {
                        "semantic_operations": ["TRANSFERS_VALUE_OUT", "WRITES_USER_BALANCE"],
                        "cyclomatic_complexity": 5,
                        "has_access_gate": True,
                    },
                },
                {
                    "label": "approve",
                    "properties": {
                        "semantic_operations": ["MODIFIES_CRITICAL_STATE"],
                        "cyclomatic_complexity": 3,
                    },
                },
            ],
            state_vars=10,
        )

        profile = self.profiler.profile(kg)

        self.assertEqual(profile.num_contracts, 1)
        self.assertEqual(profile.num_functions, 2)
        self.assertEqual(profile.num_state_variables, 10)
        self.assertFalse(profile.is_upgradeable)
        self.assertIsNotNone(profile.embedding)
        self.assertTrue(profile.has_access_control)

    def test_dex_classification(self):
        """Test DEX protocol classification."""
        kg = self._create_mock_kg(
            contracts_data=[
                {"label": "UniswapPair", "properties": {}},
            ],
            functions_data=[
                {
                    "label": "swap",
                    "properties": {
                        "semantic_operations": [
                            "TRANSFERS_VALUE_OUT",
                            "WRITES_USER_BALANCE",
                            "READS_USER_BALANCE",
                        ],
                        "cyclomatic_complexity": 10,
                    },
                },
                {
                    "label": "addLiquidity",
                    "properties": {
                        "semantic_operations": ["WRITES_USER_BALANCE", "TRANSFERS_VALUE_OUT"],
                        "cyclomatic_complexity": 8,
                    },
                },
            ] * 3,  # Repeat to get enough operations
        )

        profile = self.profiler.profile(kg)

        self.assertEqual(profile.protocol_type, "dex")

    def test_lending_classification(self):
        """Test lending protocol classification."""
        kg = self._create_mock_kg(
            contracts_data=[
                {"label": "LendingPool", "properties": {}},
            ],
            functions_data=[
                {
                    "label": "borrow",
                    "properties": {
                        "semantic_operations": [
                            "READS_ORACLE",
                            "TRANSFERS_VALUE_OUT",
                            "READS_EXTERNAL_VALUE",
                        ],
                        "cyclomatic_complexity": 15,
                    },
                },
                {
                    "label": "repay",
                    "properties": {
                        "semantic_operations": [
                            "READS_ORACLE",
                            "WRITES_USER_BALANCE",
                        ],
                        "cyclomatic_complexity": 10,
                    },
                },
            ] * 6,  # Repeat to get enough operations
        )

        profile = self.profiler.profile(kg)

        self.assertEqual(profile.protocol_type, "lending")

    def test_vault_classification(self):
        """Test vault protocol classification."""
        kg = self._create_mock_kg(
            contracts_data=[
                {"label": "Vault", "properties": {}},
            ],
            functions_data=[
                {
                    "label": "deposit",
                    "properties": {
                        "semantic_operations": ["WRITES_USER_BALANCE", "TRANSFERS_VALUE_OUT"],
                        "cyclomatic_complexity": 5,
                    },
                },
                {
                    "label": "withdraw",
                    "properties": {
                        "semantic_operations": ["WRITES_USER_BALANCE", "TRANSFERS_VALUE_OUT"],
                        "cyclomatic_complexity": 7,
                    },
                },
            ] * 3,  # Repeat
        )

        profile = self.profiler.profile(kg)

        self.assertEqual(profile.protocol_type, "vault")

    def test_oracle_consumer_classification(self):
        """Test oracle consumer classification."""
        kg = self._create_mock_kg(
            contracts_data=[
                {"label": "PriceFeed", "properties": {}},
            ],
            functions_data=[
                {
                    "label": "getLatestPrice",
                    "properties": {
                        "semantic_operations": ["READS_ORACLE", "READS_EXTERNAL_VALUE"],
                        "cyclomatic_complexity": 4,
                    },
                },
            ] * 6,  # Repeat
        )

        profile = self.profiler.profile(kg)

        self.assertEqual(profile.protocol_type, "oracle_consumer")
        self.assertTrue(profile.uses_oracles)

    def test_nft_classification(self):
        """Test NFT protocol classification."""
        kg = self._create_mock_kg(
            contracts_data=[
                {"label": "ERC721Token", "properties": {}},
            ],
            functions_data=[
                {
                    "label": "mint",
                    "properties": {
                        "semantic_operations": ["MODIFIES_CRITICAL_STATE"],
                        "cyclomatic_complexity": 5,
                    },
                },
            ],
        )

        profile = self.profiler.profile(kg)

        self.assertEqual(profile.protocol_type, "nft")

    def test_proxy_detection(self):
        """Test proxy pattern detection."""
        kg = self._create_mock_kg(
            contracts_data=[
                {
                    "label": "TransparentProxy",
                    "properties": {
                        "is_upgradeable": True,
                        "proxy_type": "transparent",
                    },
                },
            ],
            functions_data=[
                {
                    "label": "upgradeTo",
                    "properties": {
                        "semantic_operations": ["MODIFIES_CRITICAL_STATE"],
                        "cyclomatic_complexity": 3,
                    },
                },
            ],
        )

        profile = self.profiler.profile(kg)

        self.assertTrue(profile.is_upgradeable)
        self.assertEqual(profile.proxy_pattern, "transparent")

    def test_primitive_detection_amm(self):
        """Test AMM primitive detection."""
        kg = self._create_mock_kg(
            contracts_data=[{"label": "AMM", "properties": {}}],
            functions_data=[
                {
                    "label": "swap",
                    "properties": {
                        "semantic_operations": [
                            "READS_USER_BALANCE",
                            "WRITES_USER_BALANCE",
                            "TRANSFERS_VALUE_OUT",
                        ],
                        "cyclomatic_complexity": 10,
                    },
                },
            ],
        )

        profile = self.profiler.profile(kg)

        self.assertIn("amm", profile.primitives_used)

    def test_primitive_detection_flash_loan(self):
        """Test flash loan primitive detection."""
        kg = self._create_mock_kg(
            contracts_data=[{"label": "FlashLoan", "properties": {}}],
            functions_data=[
                {
                    "label": "flashLoan",
                    "properties": {
                        "semantic_operations": [
                            "CALLS_EXTERNAL",
                            "TRANSFERS_VALUE_OUT",
                            "CHECKS_PERMISSION",
                        ],
                        "cyclomatic_complexity": 12,
                    },
                },
            ],
        )

        profile = self.profiler.profile(kg)

        self.assertIn("flash_loan", profile.primitives_used)

    def test_primitive_detection_governance(self):
        """Test governance primitive detection."""
        kg = self._create_mock_kg(
            contracts_data=[{"label": "Governor", "properties": {}}],
            functions_data=[
                {
                    "label": "execute",
                    "properties": {
                        "semantic_operations": [
                            "MODIFIES_ROLES",
                            "CHECKS_PERMISSION",
                            "MODIFIES_OWNER",
                        ],
                        "cyclomatic_complexity": 8,
                    },
                },
            ],
        )

        profile = self.profiler.profile(kg)

        self.assertIn("governance", profile.primitives_used)
        self.assertTrue(profile.uses_governance)

    def test_multisig_detection(self):
        """Test multisig pattern detection."""
        kg = self._create_mock_kg(
            contracts_data=[{"label": "Multisig", "properties": {}}],
            functions_data=[
                {
                    "label": "confirmTransaction",
                    "properties": {
                        "semantic_operations": ["CHECKS_PERMISSION"],
                        "cyclomatic_complexity": 5,
                        "has_access_gate": True,
                    },
                },
            ],
        )

        profile = self.profiler.profile(kg)

        self.assertTrue(profile.uses_multisig)

    def test_timelock_detection(self):
        """Test timelock pattern detection."""
        kg = self._create_mock_kg(
            contracts_data=[{"label": "Timelock", "properties": {}}],
            functions_data=[
                {
                    "label": "queueTransaction",
                    "properties": {
                        "semantic_operations": ["MODIFIES_CRITICAL_STATE"],
                        "cyclomatic_complexity": 4,
                    },
                },
            ],
        )

        profile = self.profiler.profile(kg)

        self.assertTrue(profile.uses_timelock)

    def test_embedding_generation(self):
        """Test embedding vector generation."""
        kg = self._create_mock_kg(
            contracts_data=[{"label": "Test", "properties": {}}],
            functions_data=[
                {
                    "label": "test",
                    "properties": {
                        "semantic_operations": [
                            "TRANSFERS_VALUE_OUT",
                            "WRITES_USER_BALANCE",
                        ],
                        "cyclomatic_complexity": 1,
                    },
                },
            ],
        )

        profile = self.profiler.profile(kg)

        self.assertIsNotNone(profile.embedding)
        self.assertIsInstance(profile.embedding, list)
        self.assertEqual(len(profile.embedding), len(self.profiler.operation_vocab))

        # Check normalization (L2 norm should be 1.0)
        magnitude = math.sqrt(sum(x * x for x in profile.embedding))
        self.assertAlmostEqual(magnitude, 1.0, places=4)

    def test_complexity_metrics(self):
        """Test complexity metric calculation."""
        kg = self._create_mock_kg(
            contracts_data=[{"label": "Complex", "properties": {}}],
            functions_data=[
                {
                    "label": "simple",
                    "properties": {
                        "semantic_operations": ["TRANSFERS_VALUE_OUT"],
                        "cyclomatic_complexity": 2,
                    },
                },
                {
                    "label": "complex",
                    "properties": {
                        "semantic_operations": ["WRITES_USER_BALANCE"],
                        "cyclomatic_complexity": 15,
                    },
                },
            ],
        )

        profile = self.profiler.profile(kg)

        self.assertEqual(profile.max_function_complexity, 15)
        self.assertEqual(profile.avg_function_complexity, (2 + 15) / 2)

    def test_security_features(self):
        """Test security feature detection."""
        kg = self._create_mock_kg(
            contracts_data=[{"label": "Secure", "properties": {}}],
            functions_data=[
                {
                    "label": "secureTransfer",
                    "properties": {
                        "semantic_operations": ["TRANSFERS_VALUE_OUT"],
                        "cyclomatic_complexity": 5,
                        "has_access_gate": True,
                        "has_reentrancy_guard": True,
                    },
                },
                {
                    "label": "pause",
                    "properties": {
                        "semantic_operations": ["MODIFIES_CRITICAL_STATE"],
                        "cyclomatic_complexity": 2,
                    },
                },
            ],
        )

        profile = self.profiler.profile(kg)

        self.assertTrue(profile.has_access_control)
        self.assertTrue(profile.has_reentrancy_guards)
        self.assertTrue(profile.has_pause_mechanism)


class TestProjectDatabase(unittest.TestCase):
    """Test ProjectDatabase for similarity search."""

    def setUp(self):
        """Set up test database with sample profiles."""
        self.db = ProjectDatabase()

        # Create sample profiles
        self.profile1 = ProjectProfile(
            project_id="uniswap_v2",
            name="Uniswap V2",
            is_upgradeable=False,
            protocol_type="dex",
            primitives_used=["amm", "liquidity_pool"],
            num_contracts=5,
            num_functions=50,
            embedding=[0.8, 0.6, 0.0],  # Normalized
        )

        self.profile2 = ProjectProfile(
            project_id="sushiswap",
            name="SushiSwap",
            is_upgradeable=False,
            protocol_type="dex",
            primitives_used=["amm", "liquidity_pool", "staking"],
            num_contracts=6,
            num_functions=55,
            embedding=[0.7, 0.7, 0.1],  # Similar to profile1
        )

        self.profile3 = ProjectProfile(
            project_id="aave_v2",
            name="Aave V2",
            is_upgradeable=True,
            proxy_pattern="transparent",
            protocol_type="lending",
            primitives_used=["flash_loan", "oracle_integration"],
            num_contracts=20,
            num_functions=200,
            embedding=[0.1, 0.1, 0.99],  # Very different
        )

        self.db.add_profile(self.profile1)
        self.db.add_profile(self.profile2)
        self.db.add_profile(self.profile3)

    def test_add_profile(self):
        """Test adding profiles to database."""
        self.assertEqual(len(self.db.profiles), 3)
        self.assertIn("uniswap_v2", self.db.profiles)
        self.assertIn("sushiswap", self.db.profiles)
        self.assertIn("aave_v2", self.db.profiles)

    def test_find_similar(self):
        """Test finding similar projects."""
        # Query with DEX profile
        query = ProjectProfile(
            project_id="new_dex",
            name="New DEX",
            is_upgradeable=False,
            protocol_type="dex",
            primitives_used=["amm"],
            num_contracts=1,
            num_functions=1,
            embedding=[0.75, 0.65, 0.05],  # Similar to profile1
        )

        similar = self.db.find_similar(query, top_k=2, min_similarity=0.5)

        self.assertEqual(len(similar), 2)
        # Should find uniswap and sushiswap (both DEXes)
        found_ids = [p.project_id for p, _ in similar]
        self.assertIn("uniswap_v2", found_ids)
        self.assertIn("sushiswap", found_ids)

    def test_find_similar_excludes_self(self):
        """Test that find_similar excludes query project itself."""
        similar = self.db.find_similar(self.profile1, top_k=5)

        # Should not include profile1 itself
        found_ids = [p.project_id for p, _ in similar]
        self.assertNotIn("uniswap_v2", found_ids)

    def test_find_similar_min_threshold(self):
        """Test minimum similarity threshold filtering."""
        query = ProjectProfile(
            project_id="very_different",
            name="Very Different",
            is_upgradeable=False,
            protocol_type="utility",
            primitives_used=[],
            num_contracts=1,
            num_functions=1,
            embedding=[0.0, 0.0, 1.0],  # Orthogonal to DEXes
        )

        # High threshold should filter out dissimilar projects
        similar = self.db.find_similar(query, top_k=10, min_similarity=0.9)

        # Should find aave (similar embedding direction) but not DEXes
        self.assertLessEqual(len(similar), 1)

    def test_get_by_protocol_type(self):
        """Test getting projects by protocol type."""
        dexes = self.db.get_by_protocol_type("dex")

        self.assertEqual(len(dexes), 2)
        dex_ids = [p.project_id for p in dexes]
        self.assertIn("uniswap_v2", dex_ids)
        self.assertIn("sushiswap", dex_ids)

        lending = self.db.get_by_protocol_type("lending")
        self.assertEqual(len(lending), 1)
        self.assertEqual(lending[0].project_id, "aave_v2")

    def test_get_by_primitive(self):
        """Test getting projects by DeFi primitive."""
        amm_projects = self.db.get_by_primitive("amm")

        self.assertEqual(len(amm_projects), 2)
        amm_ids = [p.project_id for p in amm_projects]
        self.assertIn("uniswap_v2", amm_ids)
        self.assertIn("sushiswap", amm_ids)

        flash_loan_projects = self.db.get_by_primitive("flash_loan")
        self.assertEqual(len(flash_loan_projects), 1)
        self.assertEqual(flash_loan_projects[0].project_id, "aave_v2")


class TestSuccessCriteria(unittest.TestCase):
    """Test success criteria from P4-T1 spec."""

    def setUp(self):
        """Set up profiler and database."""
        self.profiler = ProjectProfiler()
        self.db = ProjectDatabase()

    def test_profile_creation_working(self):
        """✓ Profile creation working."""
        kg = Mock(spec=KnowledgeGraph)
        kg.nodes = {}
        kg.metadata = {"target": "/path/to/test.sol"}

        profile = self.profiler.profile(kg)

        self.assertIsInstance(profile, ProjectProfile)
        self.assertIsNotNone(profile.project_id)
        self.assertIsNotNone(profile.embedding)

    def test_protocol_classification_accurate(self):
        """✓ Protocol type classification accurate."""
        # Test multiple protocol types
        test_cases = [
            ("dex", ["swap"], ["WRITES_USER_BALANCE", "TRANSFERS_VALUE_OUT"] * 6),
            ("lending", ["borrow"], ["READS_ORACLE", "TRANSFERS_VALUE_OUT"] * 6),
            ("vault", ["deposit", "withdraw"], ["WRITES_USER_BALANCE", "TRANSFERS_VALUE_OUT"] * 3),
            ("oracle_consumer", ["getPrice"], ["READS_ORACLE"] * 6),
        ]

        for expected_type, fn_names, ops in test_cases:
            kg = Mock(spec=KnowledgeGraph)

            contracts = [Mock(type="Contract", label=f"{expected_type}_contract", properties={})]
            functions = [
                Mock(
                    type="Function",
                    label=name,
                    properties={
                        "semantic_operations": ops,
                        "cyclomatic_complexity": 5,
                    },
                )
                for name in fn_names
            ]

            kg.nodes = {str(i): n for i, n in enumerate(contracts + functions)}
            kg.metadata = {"target": f"/path/to/{expected_type}.sol"}

            profile = self.profiler.profile(kg)
            self.assertEqual(
                profile.protocol_type,
                expected_type,
                f"Failed to classify {expected_type}",
            )

    def test_primitive_detection_working(self):
        """✓ Primitive detection working."""
        kg = Mock(spec=KnowledgeGraph)

        contracts = [Mock(type="Contract", label="Test", properties={})]
        functions = [
            Mock(
                type="Function",
                label="test",
                properties={
                    "semantic_operations": [
                        "READS_USER_BALANCE",
                        "WRITES_USER_BALANCE",
                        "TRANSFERS_VALUE_OUT",
                        "CALLS_EXTERNAL",
                        "CHECKS_PERMISSION",
                    ],
                    "cyclomatic_complexity": 10,
                },
            )
        ]

        kg.nodes = {str(i): n for i, n in enumerate(contracts + functions)}
        kg.metadata = {"target": "/path/to/test.sol"}

        profile = self.profiler.profile(kg)

        # Should detect multiple primitives
        self.assertGreater(len(profile.primitives_used), 0)
        # AMM signature should match
        self.assertIn("amm", profile.primitives_used)
        # Flash loan signature should match
        self.assertIn("flash_loan", profile.primitives_used)

    def test_embedding_generation_for_similarity(self):
        """✓ Embedding generation for similarity."""
        # Create two similar profiles
        kg1 = Mock(spec=KnowledgeGraph)
        kg2 = Mock(spec=KnowledgeGraph)

        # Same operations
        contracts = [Mock(type="Contract", label="Test", properties={})]
        functions = [
            Mock(
                type="Function",
                label="test",
                properties={
                    "semantic_operations": ["TRANSFERS_VALUE_OUT", "WRITES_USER_BALANCE"],
                    "cyclomatic_complexity": 5,
                },
            )
        ]

        kg1.nodes = {str(i): n for i, n in enumerate(contracts + functions)}
        kg1.metadata = {"target": "/path/to/test1.sol"}

        kg2.nodes = {str(i): n for i, n in enumerate(contracts + functions)}
        kg2.metadata = {"target": "/path/to/test2.sol"}

        profile1 = self.profiler.profile(kg1)
        profile2 = self.profiler.profile(kg2)

        # Both should have embeddings
        self.assertIsNotNone(profile1.embedding)
        self.assertIsNotNone(profile2.embedding)

        # Should be highly similar (same operations)
        similarity = profile1.similarity_to(profile2)
        self.assertGreater(similarity, 0.99)


if __name__ == "__main__":
    unittest.main()
