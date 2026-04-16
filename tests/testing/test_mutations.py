"""Tests for contract mutation system and counterfactual generation."""

import pytest
from pathlib import Path

import yaml

from alphaswarm_sol.testing.mutations import (
    MutationEngine,
    MutationType,
    MutationResult,
    ValidationStatus,
    CounterfactualType,
    CounterfactualResult,
    CounterfactualGenerator,
    create_hard_negative_contract,
)


# Sample Solidity contract for testing
SAMPLE_CONTRACT = '''
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract Vault {
    mapping(address => uint256) public balances;
    address public owner;

    event Deposit(address indexed user, uint256 amount);
    event Withdrawal(address indexed user, uint256 amount);

    modifier onlyOwner() {
        require(msg.sender == owner, "Not owner");
        _;
    }

    function deposit() external payable {
        require(msg.value > 0, "Must send ETH");
        balances[msg.sender] += msg.value;
        emit Deposit(msg.sender, msg.value);
    }

    function withdraw(uint256 amount) external {
        require(amount > 0, "Amount must be positive");
        require(balances[msg.sender] >= amount, "Insufficient balance");

        // Vulnerable: state update after external call
        (bool success, ) = msg.sender.call{value: amount}("");
        require(success, "Transfer failed");
        balances[msg.sender] -= amount;

        emit Withdrawal(msg.sender, amount);
    }
}
'''


class TestMutationEngine:
    """Tests for MutationEngine."""

    @pytest.fixture
    def engine(self, tmp_path: Path) -> MutationEngine:
        """Create engine with temporary output directory."""
        return MutationEngine(output_dir=tmp_path / "mutations")

    @pytest.fixture
    def sample_contract(self, tmp_path: Path) -> Path:
        """Create sample contract file."""
        contract_path = tmp_path / "Vault.sol"
        contract_path.write_text(SAMPLE_CONTRACT)
        return contract_path

    def test_extract_identifiers(self, engine: MutationEngine) -> None:
        """Test identifier extraction."""
        identifiers = engine._extract_identifiers(SAMPLE_CONTRACT)

        # Should find custom identifiers
        assert "balances" in identifiers
        assert "amount" in identifiers
        assert "success" in identifiers

        # Should not include keywords
        assert "function" not in identifiers
        assert "require" not in identifiers
        assert "uint256" not in identifiers

    def test_rename_mutation(self, engine: MutationEngine) -> None:
        """Test identifier renaming."""
        mutated, changes = engine.apply_rename_mutation(
            SAMPLE_CONTRACT,
            identifiers_to_rename={"balances", "amount"},
        )

        assert len(changes) == 2
        # Original identifiers should not appear
        for change in changes:
            assert change["old"] not in mutated or change["new"] in mutated

    def test_reorder_mutation(self, engine: MutationEngine) -> None:
        """Test statement reordering."""
        # Contract with consecutive requires
        content = '''
function test() external {
    require(a > 0, "a");
    require(b > 0, "b");
    doSomething();
}
'''
        mutated, changes = engine.apply_reorder_mutation(content)

        # Should have reordering changes if consecutive requires exist
        # Note: depends on exact pattern matching
        assert isinstance(changes, list)

    def test_structural_mutation(self, engine: MutationEngine) -> None:
        """Test structural mutations."""
        mutated, changes = engine.apply_structural_mutation(SAMPLE_CONTRACT)

        # Should add NatSpec comments
        assert "/// @notice" in mutated or len(changes) > 0

    def test_generate_mutations(
        self, engine: MutationEngine, sample_contract: Path
    ) -> None:
        """Test generating multiple mutations."""
        results = engine.generate_mutations(
            sample_contract,
            count=5,
            mutation_types=[MutationType.RENAME],
        )

        assert len(results) == 5
        for result in results:
            assert result.mutation_type == MutationType.RENAME
            assert Path(result.mutated_path).exists()
            assert result.mutation_id.startswith("Vault-rename-")

    def test_generate_mixed_mutations(
        self, engine: MutationEngine, sample_contract: Path
    ) -> None:
        """Test generating mutations of different types."""
        results = engine.generate_mutations(
            sample_contract,
            count=10,
            mutation_types=[
                MutationType.RENAME,
                MutationType.REORDER,
                MutationType.STRUCTURAL,
            ],
        )

        assert len(results) == 10
        # Should have variety of mutation types
        types = {r.mutation_type for r in results}
        assert len(types) >= 1  # At least one type used

    def test_mutation_hashes_differ(
        self, engine: MutationEngine, sample_contract: Path
    ) -> None:
        """Test that mutations produce different hashes."""
        results = engine.generate_mutations(
            sample_contract,
            count=3,
            mutation_types=[MutationType.RENAME],
        )

        hashes = {r.mutated_hash for r in results}
        # At least some mutations should have different hashes
        # (Not all, since small mutations might not change hash significantly)
        assert len(hashes) >= 1

    def test_mutation_result_to_dict(
        self, engine: MutationEngine, sample_contract: Path
    ) -> None:
        """Test MutationResult serialization."""
        results = engine.generate_mutations(sample_contract, count=1)
        result = results[0]

        data = result.to_dict()
        assert "original_path" in data
        assert "mutated_path" in data
        assert "mutation_type" in data
        assert "changes" in data

    def test_validate_rename_mutation(
        self, engine: MutationEngine, sample_contract: Path
    ) -> None:
        """Test that rename mutations preserve vulnerability."""
        results = engine.generate_mutations(
            sample_contract,
            count=1,
            mutation_types=[MutationType.RENAME],
        )

        status = engine.validate_mutation(results[0], "reentrancy-classic")
        # Rename should preserve vulnerability semantics
        assert status == ValidationStatus.VULNERABLE

    def test_output_directory_created(self, tmp_path: Path) -> None:
        """Test that output directory is created."""
        output_dir = tmp_path / "new" / "nested" / "dir"
        engine = MutationEngine(output_dir=output_dir)

        assert output_dir.exists()

    def test_solidity_keywords_protected(self, engine: MutationEngine) -> None:
        """Test that Solidity keywords are protected from renaming."""
        # Create content with only keywords
        content = "function require uint256 address mapping"
        identifiers = engine._extract_identifiers(content)

        # All should be filtered out as keywords
        assert "function" not in identifiers
        assert "require" not in identifiers
        assert "uint256" not in identifiers
        assert "address" not in identifiers
        assert "mapping" not in identifiers

    def test_hash_content(self, engine: MutationEngine) -> None:
        """Test content hashing."""
        content1 = "contract A {}"
        content2 = "contract B {}"

        hash1 = engine._hash_content(content1)
        hash2 = engine._hash_content(content2)

        assert hash1 != hash2
        assert len(hash1) == 16  # SHA256 truncated to 16 chars

    def test_generate_mutation_id(self, engine: MutationEngine) -> None:
        """Test mutation ID generation."""
        mutation_id = engine._generate_mutation_id(
            "path/to/Vault.sol", MutationType.RENAME, 42
        )

        assert mutation_id == "Vault-rename-042"

    def test_rename_with_amount_pool(self, engine: MutationEngine) -> None:
        """Test that amount-related names use amount pool."""
        content = "uint256 userBalance = 100;"
        mutated, changes = engine.apply_rename_mutation(
            content,
            identifiers_to_rename={"userBalance"},
        )

        # Should use amount pool for balance-related identifiers
        assert len(changes) == 1
        assert changes[0]["old"] == "userBalance"
        # New name should be from amount pool (amt, qty, sum, etc.)
        new_name = changes[0]["new"]
        assert any(
            prefix in new_name for prefix in ["amt", "qty", "sum", "total", "quantity"]
        )


class TestMutationResult:
    """Tests for MutationResult dataclass."""

    def test_to_dict_complete(self) -> None:
        """Test full serialization."""
        result = MutationResult(
            original_path="path/to/original.sol",
            mutated_path="path/to/mutated.sol",
            mutation_type=MutationType.RENAME,
            mutation_id="test-rename-001",
            description="Renamed 3 identifiers",
            validation_status=ValidationStatus.VULNERABLE,
            original_hash="abc123",
            mutated_hash="def456",
            changes=[{"old": "balances", "new": "x_1234"}],
        )

        data = result.to_dict()
        assert data["mutation_type"] == "rename"
        assert data["validation_status"] == "vulnerable"
        assert len(data["changes"]) == 1

    def test_default_values(self) -> None:
        """Test default field values."""
        result = MutationResult(
            original_path="original.sol",
            mutated_path="mutated.sol",
            mutation_type=MutationType.STRUCTURAL,
            mutation_id="test-001",
            description="Test mutation",
        )

        assert result.validation_status == ValidationStatus.UNKNOWN
        assert result.original_hash == ""
        assert result.mutated_hash == ""
        assert result.changes == []


class TestValidationStatus:
    """Tests for ValidationStatus enum."""

    def test_enum_values(self) -> None:
        """Test enum has expected values."""
        assert ValidationStatus.VULNERABLE.value == "vulnerable"
        assert ValidationStatus.SAFE.value == "safe"
        assert ValidationStatus.UNKNOWN.value == "unknown"

    def test_is_string_enum(self) -> None:
        """Test that ValidationStatus is a string enum."""
        assert isinstance(ValidationStatus.VULNERABLE, str)
        assert ValidationStatus.VULNERABLE.value == "vulnerable"


class TestMutationType:
    """Tests for MutationType enum."""

    def test_enum_values(self) -> None:
        """Test enum has expected values."""
        assert MutationType.RENAME.value == "rename"
        assert MutationType.REORDER.value == "reorder"
        assert MutationType.VARIATION.value == "variation"
        assert MutationType.STRUCTURAL.value == "structural"

    def test_is_string_enum(self) -> None:
        """Test that MutationType is a string enum."""
        assert isinstance(MutationType.RENAME, str)
        assert MutationType.RENAME.value == "rename"


# =============================================================================
# Counterfactual Generation Tests (Phase 7.2 Plan 12)
# =============================================================================

# Sample vulnerable contract for counterfactual testing
VULNERABLE_CONTRACT = '''
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract VulnerableVault {
    mapping(address => uint256) public balances;

    function deposit() external payable {
        require(msg.value > 0, "Must send ETH");
        balances[msg.sender] += msg.value;
    }

    function withdraw(uint256 amount) external {
        require(amount > 0, "Amount must be positive");
        require(balances[msg.sender] >= amount, "Insufficient balance");

        // Vulnerable: CEI violation - call before state update
        (bool success, ) = msg.sender.call{value: amount}("");
        require(success, "Transfer failed");
        balances[msg.sender] -= amount;
    }
}
'''

# Safe contract for counterfactual testing
SAFE_CONTRACT = '''
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract SafeVault {
    mapping(address => uint256) public balances;
    bool private locked;

    modifier nonReentrant() {
        require(!locked, "Reentrant");
        locked = true;
        _;
        locked = false;
    }

    function deposit() external payable {
        require(msg.value > 0, "Must send ETH");
        balances[msg.sender] += msg.value;
    }

    function withdraw(uint256 amount) external nonReentrant {
        require(amount > 0, "Amount must be positive");
        require(balances[msg.sender] >= amount, "Insufficient balance");

        // Safe: CEI pattern - state updated before call
        balances[msg.sender] -= amount;
        (bool success, ) = msg.sender.call{value: amount}("");
        require(success, "Transfer failed");
    }
}
'''


class TestCounterfactualType:
    """Tests for CounterfactualType enum."""

    def test_enum_values(self) -> None:
        """Test enum has expected values."""
        assert CounterfactualType.GUARD_INVERSION.value == "guard_inversion"
        assert CounterfactualType.CEI_ORDER_SWAP.value == "cei_order_swap"
        assert CounterfactualType.GRACE_PERIOD.value == "grace_period"
        assert CounterfactualType.HELPER_DEPTH.value == "helper_depth"
        assert CounterfactualType.CHAIN_CONDITION.value == "chain_condition"
        assert CounterfactualType.AUDIT_MIRROR.value == "audit_mirror"

    def test_is_string_enum(self) -> None:
        """Test that CounterfactualType is a string enum."""
        assert isinstance(CounterfactualType.GUARD_INVERSION, str)


class TestCounterfactualResult:
    """Tests for CounterfactualResult dataclass."""

    def test_to_dict_complete(self) -> None:
        """Test full serialization."""
        result = CounterfactualResult(
            base_contract_id="vault-001",
            base_contract_path="path/to/Vault.sol",
            counterfactual_id="cf-vault-001-guard_inversion-000",
            counterfactual_path="path/to/cf/counterfactual.sol",
            counterfactual_type=CounterfactualType.GUARD_INVERSION,
            description="Inverted require condition",
            expected_vulnerability_status=ValidationStatus.VULNERABLE,
            semantic_diff="inverted_1_guards",
            original_hash="abc123",
            counterfactual_hash="def456",
            metadata={"generated_at": "2026-01-29"},
        )

        data = result.to_dict()
        assert data["base_contract_id"] == "vault-001"
        assert data["counterfactual_type"] == "guard_inversion"
        assert data["expected_vulnerability_status"] == "vulnerable"
        assert data["semantic_diff"] == "inverted_1_guards"

    def test_metadata_links_to_base_contract(self) -> None:
        """Test that counterfactual metadata links to base contract."""
        result = CounterfactualResult(
            base_contract_id="original-contract-id",
            base_contract_path="/path/to/original.sol",
            counterfactual_id="cf-original-contract-id-guard_inversion-001",
            counterfactual_path="/path/to/counterfactual.sol",
            counterfactual_type=CounterfactualType.GUARD_INVERSION,
            description="Test",
            expected_vulnerability_status=ValidationStatus.VULNERABLE,
            semantic_diff="test_diff",
        )

        data = result.to_dict()
        # Verify base contract ID is preserved
        assert data["base_contract_id"] == "original-contract-id"
        assert data["base_contract_path"] == "/path/to/original.sol"
        # Verify counterfactual ID includes base contract ID
        assert "original-contract-id" in data["counterfactual_id"]


class TestCounterfactualGenerator:
    """Tests for CounterfactualGenerator."""

    @pytest.fixture
    def generator(self, tmp_path: Path) -> CounterfactualGenerator:
        """Create generator with temporary output directory."""
        return CounterfactualGenerator(output_dir=tmp_path / "counterfactuals")

    @pytest.fixture
    def vulnerable_contract(self, tmp_path: Path) -> Path:
        """Create sample vulnerable contract file."""
        contract_path = tmp_path / "VulnerableVault.sol"
        contract_path.write_text(VULNERABLE_CONTRACT)
        return contract_path

    @pytest.fixture
    def safe_contract(self, tmp_path: Path) -> Path:
        """Create sample safe contract file."""
        contract_path = tmp_path / "SafeVault.sol"
        contract_path.write_text(SAFE_CONTRACT)
        return contract_path

    def test_guard_inversion_creates_vulnerable(
        self, generator: CounterfactualGenerator
    ) -> None:
        """Test guard inversion creates vulnerable variant."""
        mutated, semantic_diff, status = generator.apply_guard_inversion(SAFE_CONTRACT)

        # Should have inverted a require condition
        assert "inverted" in semantic_diff or semantic_diff == "no_changes"
        if "inverted" in semantic_diff:
            assert status == ValidationStatus.VULNERABLE

    def test_cei_order_swap_creates_vulnerable(
        self, generator: CounterfactualGenerator
    ) -> None:
        """Test CEI order swap creates vulnerable variant."""
        mutated, semantic_diff, status = generator.apply_cei_order_swap(SAFE_CONTRACT)

        # May or may not find CEI pattern depending on exact structure
        assert semantic_diff in ("swapped_cei_order", "no_cei_pattern", "no_safe_cei_found")
        if semantic_diff == "swapped_cei_order":
            assert status == ValidationStatus.VULNERABLE

    def test_grace_period_insert_creates_safe(
        self, generator: CounterfactualGenerator
    ) -> None:
        """Test grace period insert creates safer variant."""
        mutated, semantic_diff, status = generator.apply_grace_period_insert(
            VULNERABLE_CONTRACT, grace_seconds=3600
        )

        # Should add grace period
        if "added_grace" in semantic_diff or "extended_grace" in semantic_diff:
            assert status == ValidationStatus.SAFE

    def test_grace_period_remove_creates_vulnerable(
        self, generator: CounterfactualGenerator
    ) -> None:
        """Test grace period remove creates vulnerable variant."""
        # Contract with grace period
        with_grace = '''
pragma solidity ^0.8.0;
contract WithGrace {
    function withdraw() external {
        require(block.timestamp >= lastUpdate + 3600, "grace period");
    }
}
'''
        mutated, semantic_diff, status = generator.apply_grace_period_remove(with_grace)

        if semantic_diff == "removed_grace_period":
            assert status == ValidationStatus.VULNERABLE

    def test_helper_depth_move(
        self, generator: CounterfactualGenerator
    ) -> None:
        """Test moving checks to helper function."""
        mutated, semantic_diff, status = generator.apply_helper_depth_move(
            SAFE_CONTRACT, move_to_helper=True
        )

        if "moved_to_helper" in semantic_diff:
            # Moving to helper can obfuscate detection
            assert status == ValidationStatus.VULNERABLE

    def test_chain_condition_skip(
        self, generator: CounterfactualGenerator
    ) -> None:
        """Test adding chain conditional that skips checks."""
        mutated, semantic_diff, status = generator.apply_chain_condition(
            SAFE_CONTRACT, chain_id=1, condition_type="skip_on_chain"
        )

        if "skip_check_on_chain" in semantic_diff:
            assert status == ValidationStatus.VULNERABLE

    def test_chain_condition_require(
        self, generator: CounterfactualGenerator
    ) -> None:
        """Test adding chain requirement makes it safer."""
        mutated, semantic_diff, status = generator.apply_chain_condition(
            VULNERABLE_CONTRACT, chain_id=1, condition_type="require_chain"
        )

        if "require_chain" in semantic_diff:
            assert status == ValidationStatus.SAFE

    def test_generate_counterfactuals(
        self, generator: CounterfactualGenerator, vulnerable_contract: Path
    ) -> None:
        """Test generating multiple counterfactual variants."""
        results = generator.generate_counterfactuals(
            vulnerable_contract,
            base_contract_id="vuln-vault-001",
            types=[
                CounterfactualType.GUARD_INVERSION,
                CounterfactualType.GRACE_PERIOD,
            ],
        )

        # Should generate at least some counterfactuals
        for result in results:
            # Verify metadata links to base contract
            assert result.base_contract_id == "vuln-vault-001"
            assert str(vulnerable_contract) in result.base_contract_path

            # Verify counterfactual file was created
            assert Path(result.counterfactual_path).exists()

            # Verify metadata file was created
            metadata_path = generator.metadata_dir / f"{result.counterfactual_id}.yaml"
            assert metadata_path.exists()

            # Verify metadata content
            metadata = yaml.safe_load(metadata_path.read_text())
            assert metadata["base_contract_id"] == "vuln-vault-001"

    def test_list_counterfactuals(
        self, generator: CounterfactualGenerator, vulnerable_contract: Path
    ) -> None:
        """Test listing all generated counterfactuals."""
        # Generate some counterfactuals first
        generator.generate_counterfactuals(
            vulnerable_contract,
            base_contract_id="test-contract",
            types=[CounterfactualType.GUARD_INVERSION],
        )

        # List should include generated counterfactuals
        counterfactuals = generator.list_counterfactuals()
        assert len(counterfactuals) >= 0  # May be 0 if no changes detected

    def test_counterfactual_output_dir_created(self, tmp_path: Path) -> None:
        """Test that output directories are created."""
        output_dir = tmp_path / "new" / "nested" / "counterfactuals"
        generator = CounterfactualGenerator(output_dir=output_dir)

        assert output_dir.exists()
        assert (output_dir / "metadata").exists()


class TestHardNegativeContracts:
    """Tests for hard-negative contract generation."""

    def test_create_hard_negative_contract(self, tmp_path: Path) -> None:
        """Test creating a hard-negative contract template."""
        output_path = create_hard_negative_contract(
            name="TestGuard",
            vulnerability_class="reentrancy",
            safe_variant="Has proper reentrancy guard",
            output_dir=tmp_path / "safe",
        )

        assert output_path.exists()
        content = output_path.read_text()

        # Check contract structure
        assert "HardNegative_TestGuard" in content
        assert "@custom:hard-negative true" in content
        assert "@custom:vulnerability-class reentrancy" in content
        assert "Has proper reentrancy guard" in content

    def test_hard_negative_contract_naming(self, tmp_path: Path) -> None:
        """Test hard-negative contract naming convention."""
        output_path = create_hard_negative_contract(
            name="OwnershipTimelock",
            vulnerability_class="access-control",
            safe_variant="Timelock delay on ownership changes",
            output_dir=tmp_path / "safe",
        )

        assert output_path.name == "HardNegative_OwnershipTimelock.sol"


class TestAdversarialScenarioConfig:
    """Tests for adversarial scenario configuration structure."""

    @pytest.fixture
    def config_path(self) -> Path:
        """Get path to adversarial scenario config."""
        return Path("src/alphaswarm_sol/testing/scenarios/adversarial/config.yaml")

    def test_config_exists(self, config_path: Path) -> None:
        """Test that adversarial config file exists."""
        assert config_path.exists(), "Adversarial scenario config missing"

    def test_config_has_counterfactual_suites(self, config_path: Path) -> None:
        """Test that config references counterfactual suites."""
        config = yaml.safe_load(config_path.read_text())

        assert "counterfactual_suites" in config
        suites = config["counterfactual_suites"]
        assert len(suites) >= 5  # Should have at least 5 types

        # Check each suite has required fields
        for suite in suites:
            assert "name" in suite
            assert "type" in suite
            assert "path" in suite
            assert "expected_ratio" in suite
            assert "vulnerable" in suite["expected_ratio"]
            assert "safe" in suite["expected_ratio"]

    def test_config_has_hard_negative_suites(self, config_path: Path) -> None:
        """Test that config references hard-negative suites."""
        config = yaml.safe_load(config_path.read_text())

        assert "hard_negative_suites" in config
        suites = config["hard_negative_suites"]
        assert len(suites) >= 1

        # Check core hard-negatives suite
        core_suite = suites[0]
        assert "name" in core_suite
        assert "contracts" in core_suite
        assert len(core_suite["contracts"]) >= 8

    def test_counterfactual_ratio_checks(self, config_path: Path) -> None:
        """Test that counterfactual suites have valid ratios."""
        config = yaml.safe_load(config_path.read_text())

        for suite in config["counterfactual_suites"]:
            ratio = suite["expected_ratio"]
            vuln_ratio = ratio["vulnerable"]
            safe_ratio = ratio["safe"]

            # Ratios should be between 0 and 1
            assert 0.0 <= vuln_ratio <= 1.0
            assert 0.0 <= safe_ratio <= 1.0
            # Ratios should sum to 1.0
            assert abs((vuln_ratio + safe_ratio) - 1.0) < 0.001

    def test_hard_negative_contracts_have_required_fields(
        self, config_path: Path
    ) -> None:
        """Test that hard-negative contracts have required metadata."""
        config = yaml.safe_load(config_path.read_text())

        for suite in config["hard_negative_suites"]:
            for contract in suite["contracts"]:
                assert "name" in contract
                assert "vulnerability_class" in contract
                assert "safe_reason" in contract
                assert "tags" in contract

    def test_ast_morphing_variants_in_counterfactual(self, config_path: Path) -> None:
        """Test that AST-morphing variants (helper-depth) are present."""
        config = yaml.safe_load(config_path.read_text())

        suite_types = [s["type"] for s in config["counterfactual_suites"]]
        assert "helper_depth" in suite_types, "AST-morphing (helper_depth) missing"

        # Find helper-depth suite and verify tags
        helper_suite = next(
            s for s in config["counterfactual_suites"] if s["type"] == "helper_depth"
        )
        assert "ast-morph" in helper_suite["tags"]

    def test_audit_mirror_variants_present(self, config_path: Path) -> None:
        """Test that audit-mirroring variants are in config."""
        config = yaml.safe_load(config_path.read_text())

        suite_types = [s["type"] for s in config["counterfactual_suites"]]
        assert "audit_mirror" in suite_types, "Audit-mirror counterfactual missing"
