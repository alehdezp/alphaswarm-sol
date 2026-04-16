"""Tests for Test Builder Agent and Foundry Integration.

Tests the TestBuilderAgent, FoundryRunner, and related components
from Plan 05.2-05.
"""

import pytest
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock, patch

from alphaswarm_sol.agents.roles.foundry import (
    ForgeBuildResult,
    ForgeTestResult,
    FoundryRunner,
)
from alphaswarm_sol.agents.roles.test_builder import (
    GeneratedTest,
    TestBuilderAgent,
    TestGenerationConfig,
)
from alphaswarm_sol.agents.runtime import AgentRole


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_runtime():
    """Create a mock agent runtime."""
    runtime = MagicMock()
    runtime.spawn_agent = AsyncMock(
        return_value=MagicMock(
            content="""Here's the exploit test:
```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

import "forge-std/Test.sol";

contract ExploitTest is Test {
    function setUp() public {
        // Setup
    }

    function test_exploit() public {
        assertTrue(true);
    }
}
```
expected_outcome: Exploit drains funds from vulnerable contract
"""
        )
    )
    return runtime


@pytest.fixture
def mock_bead():
    """Create a mock vulnerability bead."""
    bead = MagicMock()
    bead.id = "VKG-001"
    bead.vulnerability_class = "reentrancy"
    bead.severity.value = "critical"
    bead.pattern_context.pattern_name = "Classic Reentrancy"
    bead.pattern_context.why_flagged = "External call before state update"
    bead.vulnerable_code.source = """function withdraw() external {
    uint256 amount = balances[msg.sender];
    (bool success, ) = msg.sender.call{value: amount}("");
    require(success);
    balances[msg.sender] = 0;
}"""
    bead.vulnerable_code.file_path = "src/Vault.sol"
    bead.vulnerable_code.start_line = 42
    bead.test_context.attack_scenario = "Deploy attacker contract, call withdraw in fallback"
    bead.test_context.expected_outcome = "Drain contract balance"
    return bead


@pytest.fixture
def mock_vulndocs():
    """Create a mock VulnDocs retriever."""
    mock = MagicMock()
    mock.retrieve.return_value = [
        MagicMock(title="Reentrancy Pattern", content="CEI violation detection guide...")
    ]
    return mock


# =============================================================================
# ForgeTestResult Tests
# =============================================================================


class TestForgeTestResult:
    """Tests for ForgeTestResult dataclass."""

    def test_to_dict(self):
        """Should convert to dictionary correctly."""
        result = ForgeTestResult(
            test_name="ExploitTest::test_exploit",
            passed=True,
            gas_used=12345,
            duration_ms=100,
        )
        d = result.to_dict()

        assert d["test_name"] == "ExploitTest::test_exploit"
        assert d["passed"] is True
        assert d["gas_used"] == 12345
        assert d["duration_ms"] == 100
        assert d["failure_reason"] is None

    def test_from_dict(self):
        """Should create from dictionary."""
        data = {
            "test_name": "test_exploit",
            "passed": False,
            "failure_reason": "Assertion failed",
        }
        result = ForgeTestResult.from_dict(data)

        assert result.test_name == "test_exploit"
        assert result.passed is False
        assert result.failure_reason == "Assertion failed"


# =============================================================================
# ForgeBuildResult Tests
# =============================================================================


class TestForgeBuildResult:
    """Tests for ForgeBuildResult dataclass."""

    def test_to_dict(self):
        """Should convert to dictionary correctly."""
        result = ForgeBuildResult(
            success=False,
            errors=["Error: undefined symbol"],
            warnings=["Warning: unused variable"],
        )
        d = result.to_dict()

        assert d["success"] is False
        assert "Error: undefined symbol" in d["errors"]
        assert "Warning: unused variable" in d["warnings"]

    def test_from_dict(self):
        """Should create from dictionary."""
        data = {
            "success": True,
            "errors": [],
            "warnings": ["Minor warning"],
        }
        result = ForgeBuildResult.from_dict(data)

        assert result.success is True
        assert len(result.errors) == 0
        assert len(result.warnings) == 1


# =============================================================================
# GeneratedTest Tests
# =============================================================================


class TestGeneratedTest:
    """Tests for GeneratedTest dataclass."""

    def test_test_passed_true(self):
        """test_passed should return True when any test passes."""
        gen_test = GeneratedTest(
            bead_id="VKG-001",
            test_code="contract Test {}",
            test_file="test/Exploit.t.sol",
            expected_outcome="Exploit succeeds",
            test_results=[
                ForgeTestResult("test1", False),
                ForgeTestResult("test2", True),
            ],
        )

        assert gen_test.test_passed is True

    def test_test_passed_false(self):
        """test_passed should return False when all tests fail."""
        gen_test = GeneratedTest(
            bead_id="VKG-001",
            test_code="contract Test {}",
            test_file="test/Exploit.t.sol",
            expected_outcome="Exploit succeeds",
            test_results=[
                ForgeTestResult("test1", False),
                ForgeTestResult("test2", False),
            ],
        )

        assert gen_test.test_passed is False

    def test_test_passed_no_results(self):
        """test_passed should return False when no test results."""
        gen_test = GeneratedTest(
            bead_id="VKG-001",
            test_code="contract Test {}",
            test_file="test/Exploit.t.sol",
            expected_outcome="Exploit succeeds",
        )

        assert gen_test.test_passed is False

    def test_to_dict(self):
        """Should convert to dictionary with all fields."""
        gen_test = GeneratedTest(
            bead_id="VKG-001",
            test_code="contract Test {}",
            test_file="test/Exploit.t.sol",
            expected_outcome="Exploit succeeds",
            compile_result=ForgeBuildResult(success=True),
            test_results=[ForgeTestResult("test_exploit", True)],
            vulndocs_used=["Reentrancy Pattern"],
        )

        d = gen_test.to_dict()

        assert d["bead_id"] == "VKG-001"
        assert d["compile_success"] is True
        assert d["test_passed"] is True
        assert "Reentrancy Pattern" in d["vulndocs_used"]


# =============================================================================
# FoundryRunner Tests
# =============================================================================


class TestFoundryRunner:
    """Tests for FoundryRunner class."""

    def test_write_test(self, tmp_path):
        """Should write test file to correct location."""
        # Create a mock runner without validation
        runner = FoundryRunner.__new__(FoundryRunner)
        runner.project_path = tmp_path

        test_code = """// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;
contract ExploitTest {}"""

        path = runner.write_test(test_code, "test/Exploit.t.sol")

        assert path.exists()
        assert path.read_text() == test_code
        assert path.name == "Exploit.t.sol"

    def test_parse_test_output_success(self):
        """Should parse successful test JSON output."""
        runner = FoundryRunner.__new__(FoundryRunner)

        stdout = '{"test_results": {"ExploitTest": {"test_exploit": {"status": "Success", "gas": 12345}}}}'
        results = runner._parse_test_output(stdout, "", 0)

        assert len(results) == 1
        assert results[0].passed is True
        assert results[0].gas_used == 12345
        assert "ExploitTest" in results[0].test_name

    def test_parse_test_output_failure(self):
        """Should parse failed test JSON output."""
        runner = FoundryRunner.__new__(FoundryRunner)

        stdout = '{"test_results": {"ExploitTest": {"test_exploit": {"status": "Failed", "reason": "assertion failed"}}}}'
        results = runner._parse_test_output(stdout, "", 1)

        assert len(results) == 1
        assert results[0].passed is False
        assert "assertion failed" in results[0].failure_reason

    def test_parse_test_output_multiple_tests(self):
        """Should parse multiple test results."""
        runner = FoundryRunner.__new__(FoundryRunner)

        stdout = '{"test_results": {"ExploitTest": {"test_one": {"status": "Success", "gas": 100}, "test_two": {"status": "Failed", "reason": "revert"}}}}'
        results = runner._parse_test_output(stdout, "", 1)

        assert len(results) == 2
        passed = [r for r in results if r.passed]
        failed = [r for r in results if not r.passed]
        assert len(passed) == 1
        assert len(failed) == 1

    def test_fallback_parse_pass(self):
        """Should fallback parse [PASS] format."""
        runner = FoundryRunner.__new__(FoundryRunner)

        combined = "[PASS] test_exploit (gas: 12345)"
        results = runner._fallback_parse(combined, "", 0)

        assert len(results) == 1
        assert results[0].passed is True
        assert results[0].gas_used == 12345

    def test_fallback_parse_fail(self):
        """Should fallback parse [FAIL] format."""
        runner = FoundryRunner.__new__(FoundryRunner)

        combined = "[FAIL. reason] test_exploit"
        results = runner._fallback_parse(combined, "", 1)

        assert len(results) == 1
        assert results[0].passed is False


# =============================================================================
# TestBuilderAgent Tests
# =============================================================================


class TestTestBuilderAgent:
    """Tests for TestBuilderAgent class."""

    @pytest.mark.asyncio
    async def test_generate_test_success(self, mock_runtime, mock_bead, tmp_path):
        """Should generate and write test successfully."""
        with patch.object(FoundryRunner, "__init__", return_value=None):
            builder = TestBuilderAgent(
                runtime=mock_runtime,
                project_path=tmp_path,
                config=TestGenerationConfig(include_vulndocs=False),
            )
            builder.foundry = MagicMock()
            builder.foundry.build.return_value = ForgeBuildResult(success=True)
            builder.foundry.test.return_value = [ForgeTestResult("test_exploit", True)]
            builder.foundry.write_test.return_value = tmp_path / "test.sol"

            result = await builder.generate_test(mock_bead)

        assert result.bead_id == "VKG-001"
        assert "ExploitTest" in result.test_code
        assert result.test_passed

    @pytest.mark.asyncio
    async def test_vulndocs_integration(self, mock_runtime, mock_bead, mock_vulndocs, tmp_path):
        """Should retrieve VulnDocs for grounding tests."""
        with patch.object(FoundryRunner, "__init__", return_value=None):
            builder = TestBuilderAgent(
                runtime=mock_runtime,
                project_path=tmp_path,
                config=TestGenerationConfig(include_vulndocs=True),
                vulndocs_retriever=mock_vulndocs,
            )
            builder.foundry = MagicMock()
            builder.foundry.build.return_value = ForgeBuildResult(success=True)
            builder.foundry.test.return_value = []
            builder.foundry.write_test.return_value = tmp_path / "test.sol"

            result = await builder.generate_test(mock_bead)

        mock_vulndocs.retrieve.assert_called_once()
        assert "Reentrancy Pattern" in result.vulndocs_used

    @pytest.mark.asyncio
    async def test_compile_retry_on_failure(self, mock_runtime, mock_bead, tmp_path):
        """Should retry compilation on failure with error feedback."""
        with patch.object(FoundryRunner, "__init__", return_value=None):
            builder = TestBuilderAgent(
                runtime=mock_runtime,
                project_path=tmp_path,
                config=TestGenerationConfig(max_attempts=3, include_vulndocs=False),
            )
            builder.foundry = MagicMock()
            # First compile fails, second succeeds
            builder.foundry.build.side_effect = [
                ForgeBuildResult(success=False, errors=["Error: undefined"]),
                ForgeBuildResult(success=True),
            ]
            builder.foundry.test.return_value = []
            builder.foundry.write_test.return_value = tmp_path / "test.sol"

            await builder.generate_test(mock_bead)

        # Should have called spawn_agent twice (initial + fix)
        assert mock_runtime.spawn_agent.call_count == 2

    @pytest.mark.asyncio
    async def test_max_retry_attempts(self, mock_runtime, mock_bead, tmp_path):
        """Should stop retrying after max attempts."""
        with patch.object(FoundryRunner, "__init__", return_value=None):
            builder = TestBuilderAgent(
                runtime=mock_runtime,
                project_path=tmp_path,
                config=TestGenerationConfig(max_attempts=2, include_vulndocs=False),
            )
            builder.foundry = MagicMock()
            # All compiles fail
            builder.foundry.build.return_value = ForgeBuildResult(
                success=False, errors=["Error: still broken"]
            )
            builder.foundry.test.return_value = []
            builder.foundry.write_test.return_value = tmp_path / "test.sol"

            result = await builder.generate_test(mock_bead)

        # Should have called spawn_agent twice (initial + 1 retry)
        assert mock_runtime.spawn_agent.call_count == 2
        # Test results should be empty since compile failed
        assert len(result.test_results) == 0

    def test_extract_test_code_solidity_block(self):
        """Should extract Solidity from markdown code block."""
        builder = TestBuilderAgent.__new__(TestBuilderAgent)

        response = """Here's the test:
```solidity
contract Test {
    function test_exploit() public {}
}
```
"""
        code = builder._extract_test_code(response)

        assert "contract Test" in code
        assert "test_exploit" in code

    def test_extract_test_code_generic_block(self):
        """Should extract from generic code block."""
        builder = TestBuilderAgent.__new__(TestBuilderAgent)

        response = """Here's the test:
```
contract Test {}
```
"""
        code = builder._extract_test_code(response)

        assert "contract Test" in code

    def test_extract_expected_outcome(self):
        """Should extract expected outcome from response."""
        builder = TestBuilderAgent.__new__(TestBuilderAgent)

        response = """Test code here...
expected_outcome: Attacker drains all funds from the vault"""

        outcome = builder._extract_expected_outcome(response)

        assert "drains all funds" in outcome

    def test_extract_expected_outcome_default(self):
        """Should return default when no outcome found."""
        builder = TestBuilderAgent.__new__(TestBuilderAgent)

        response = "Just some code without outcome"

        outcome = builder._extract_expected_outcome(response)

        assert "demonstrates vulnerability" in outcome.lower()

    def test_generate_test_filename(self, mock_bead):
        """Should generate safe filename from bead ID."""
        builder = TestBuilderAgent.__new__(TestBuilderAgent)
        builder.config = TestGenerationConfig()

        filename = builder._generate_test_filename(mock_bead)

        assert "VKG_001" in filename
        assert filename.endswith(".t.sol")
        assert filename.startswith("test/")


# =============================================================================
# TestGenerationConfig Tests
# =============================================================================


class TestTestGenerationConfig:
    """Tests for TestGenerationConfig."""

    def test_default_values(self):
        """Should have sensible defaults."""
        config = TestGenerationConfig()

        assert config.max_attempts == 3
        assert config.include_vulndocs is True
        assert config.test_dir == "test"
        assert config.verbose is False

    def test_custom_values(self):
        """Should accept custom values."""
        config = TestGenerationConfig(
            max_attempts=5,
            include_vulndocs=False,
            test_dir="tests",
            verbose=True,
        )

        assert config.max_attempts == 5
        assert config.include_vulndocs is False
        assert config.test_dir == "tests"
        assert config.verbose is True

    def test_to_dict(self):
        """Should convert to dictionary."""
        config = TestGenerationConfig(max_attempts=5)
        d = config.to_dict()

        assert d["max_attempts"] == 5
        assert "include_vulndocs" in d
        assert "test_dir" in d
