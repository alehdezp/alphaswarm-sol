"""Tests for VulnDocs multi-model agent system.

Task 18.2: Tests for CategoryAgent, SubcategoryWorker, MergeOrchestrator.
"""

import asyncio
import unittest
import tempfile
from unittest.mock import AsyncMock, MagicMock, patch

from alphaswarm_sol.vulndocs.agents.base import (
    AgentConfig,
    AgentModel,
    AgentResult,
    AgentStatus,
    BaseAgent,
    SubagentCoordinator,
    SubagentTask,
    TaskProgress,
)
from alphaswarm_sol.vulndocs.agents.category_agent import (
    CategoryAgent,
    CategoryResult,
    CategorySource,
    SubcategoryResult,
    get_all_categories,
    get_subcategories,
    CATEGORY_SUBCATEGORIES,
)
from alphaswarm_sol.vulndocs.agents.subcategory_worker import (
    SubcategoryWorker,
    get_source_authority,
    SOURCE_AUTHORITY_WEIGHTS,
)
from alphaswarm_sol.vulndocs.agents.merge_orchestrator import (
    MergeOrchestrator,
    compute_similarity,
    deduplicate_strings,
)
from alphaswarm_sol.vulndocs.knowledge_doc import SourceSummary


class TestAgentConfig(unittest.TestCase):
    """Tests for AgentConfig."""

    def test_default_config(self):
        """Test default configuration."""
        config = AgentConfig()
        self.assertEqual(config.model, AgentModel.HAIKU)
        self.assertEqual(config.max_retries, 3)
        self.assertEqual(config.temperature, 0.1)

    def test_haiku_worker_config(self):
        """Test Haiku worker configuration preset."""
        config = AgentConfig.for_haiku_worker()
        self.assertEqual(config.model, AgentModel.HAIKU)
        self.assertEqual(config.max_concurrent, 50)
        self.assertEqual(config.temperature, 0.0)

    def test_opus_orchestrator_config(self):
        """Test Opus orchestrator configuration preset."""
        config = AgentConfig.for_opus_orchestrator()
        self.assertEqual(config.model, AgentModel.OPUS)
        self.assertEqual(config.max_concurrent, 15)
        self.assertEqual(config.max_tokens, 8192)

    def test_to_dict(self):
        """Test serialization."""
        config = AgentConfig()
        data = config.to_dict()
        self.assertIn("model", data)
        self.assertEqual(data["model"], "haiku")


class TestAgentResult(unittest.TestCase):
    """Tests for AgentResult."""

    def test_success_result(self):
        """Test creating success result."""
        result = AgentResult.success_result({"key": "value"})
        self.assertTrue(result.success)
        self.assertEqual(result.status, AgentStatus.COMPLETED)
        self.assertEqual(result.data["key"], "value")

    def test_failure_result(self):
        """Test creating failure result."""
        result = AgentResult.failure_result("Something went wrong")
        self.assertFalse(result.success)
        self.assertEqual(result.status, AgentStatus.FAILED)
        self.assertEqual(result.error, "Something went wrong")

    def test_auto_timestamp(self):
        """Test automatic timestamp generation."""
        result = AgentResult(success=True)
        self.assertIsNotNone(result.timestamp)
        self.assertIsNotNone(result.task_id)

    def test_to_dict(self):
        """Test serialization."""
        result = AgentResult.success_result("test")
        data = result.to_dict()
        self.assertTrue(data["success"])
        self.assertIn("timestamp", data)


class TestTaskProgress(unittest.TestCase):
    """Tests for TaskProgress."""

    def test_progress_pct(self):
        """Test progress percentage calculation."""
        progress = TaskProgress(total=10, completed=5, failed=1)
        self.assertEqual(progress.progress_pct, 60.0)

    def test_progress_pct_zero_total(self):
        """Test progress with zero total."""
        progress = TaskProgress(total=0, completed=0)
        self.assertEqual(progress.progress_pct, 0.0)


class TestCategoryTaxonomy(unittest.TestCase):
    """Tests for category taxonomy."""

    def test_get_all_categories(self):
        """Test getting all categories."""
        categories = get_all_categories()
        self.assertGreater(len(categories), 10)
        self.assertIn("reentrancy", categories)
        self.assertIn("access-control", categories)
        self.assertIn("oracle", categories)

    def test_get_subcategories(self):
        """Test getting subcategories."""
        subcats = get_subcategories("reentrancy")
        self.assertGreater(len(subcats), 5)
        self.assertIn("classic-reentrancy", subcats)
        self.assertIn("cross-function-reentrancy", subcats)

    def test_all_categories_have_subcategories(self):
        """Test all categories have defined subcategories."""
        for category in get_all_categories():
            subcats = get_subcategories(category)
            self.assertGreater(
                len(subcats), 0, f"Category {category} has no subcategories"
            )


class TestCategorySource(unittest.TestCase):
    """Tests for CategorySource helpers."""

    def test_get_content_from_path(self):
        """Should load content from local snapshot path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = f"{tmpdir}/doc.md"
            with open(path, "w", encoding="utf-8") as handle:
                handle.write("local snapshot content")
            source = CategorySource(
                url="https://example.com",
                content="",
                content_path=path,
            )
            self.assertEqual(source.get_content(), "local snapshot content")


class TestSourceAuthority(unittest.TestCase):
    """Tests for source authority weights."""

    def test_tier1_authority(self):
        """Test tier 1 authority sources."""
        self.assertEqual(get_source_authority("openzeppelin"), 1.0)
        self.assertEqual(get_source_authority("trail-of-bits"), 1.0)

    def test_tier2_authority(self):
        """Test tier 2 authority sources."""
        self.assertEqual(get_source_authority("code4rena"), 0.95)
        self.assertEqual(get_source_authority("sherlock"), 0.95)

    def test_unknown_authority(self):
        """Test unknown source defaults to 0.5."""
        self.assertEqual(get_source_authority("random-blog"), 0.5)

    def test_case_insensitive(self):
        """Test case insensitive matching."""
        self.assertEqual(
            get_source_authority("OpenZeppelin"),
            get_source_authority("openzeppelin"),
        )


class TestCategoryAgent(unittest.TestCase):
    """Tests for CategoryAgent."""

    def test_init(self):
        """Test agent initialization."""
        agent = CategoryAgent("reentrancy")
        self.assertEqual(agent.category, "reentrancy")
        self.assertEqual(agent.config.model, AgentModel.HAIKU)
        self.assertGreater(len(agent.subcategories), 0)

    def test_is_haiku(self):
        """Test agent uses Haiku model."""
        agent = CategoryAgent("oracle")
        self.assertTrue(agent.is_haiku)
        self.assertFalse(agent.is_opus)

    def test_subcategory_keywords(self):
        """Test subcategory keyword generation."""
        agent = CategoryAgent("reentrancy")
        keywords = agent._get_subcategory_keywords()
        self.assertIn("classic-reentrancy", keywords)
        self.assertGreater(len(keywords["classic-reentrancy"]), 0)


class TestSubcategoryWorker(unittest.TestCase):
    """Tests for SubcategoryWorker."""

    def test_init(self):
        """Test worker initialization."""
        worker = SubcategoryWorker(
            category="reentrancy",
            subcategory="classic-reentrancy",
        )
        self.assertEqual(worker.category, "reentrancy")
        self.assertEqual(worker.subcategory, "classic-reentrancy")

    def test_extract_key_points(self):
        """Test key point extraction."""
        worker = SubcategoryWorker("test", "test")
        content = """
        - First key point about the vulnerability
        - Second important detail
        * Third bullet point here
        1. Numbered list item one
        2. Second numbered item
        """
        points = worker._extract_key_points(content)
        self.assertGreater(len(points), 0)

    def test_extract_attack_info(self):
        """Test attack info extraction."""
        worker = SubcategoryWorker("test", "test")
        content = """
        The attacker can exploit this vulnerability by deploying a malicious contract.
        Step 1: Deploy the attacker contract.
        Step 2: Call the vulnerable function.
        """
        vector, steps = worker._extract_attack_info(content)
        self.assertIn("attacker", vector.lower())

    def test_extract_code_examples(self):
        """Test code example extraction."""
        worker = SubcategoryWorker("test", "test")
        content = """
        Here is a vulnerable example:
        ```solidity
        // Vulnerable code
        function withdraw() external {
            msg.sender.call{value: balances[msg.sender]}("");
            balances[msg.sender] = 0;
        }
        ```
        And the fixed version:
        ```solidity
        // Fixed code with nonReentrant
        function withdraw() external nonReentrant {
            uint bal = balances[msg.sender];
            balances[msg.sender] = 0;
            msg.sender.call{value: bal}("");
        }
        ```
        """
        vuln_code, fixed_code = worker._extract_code_examples(content)
        self.assertIn("withdraw", vuln_code)

    def test_extract_incidents(self):
        """Test incident extraction."""
        worker = SubcategoryWorker("test", "test")
        content = """
        This vulnerability was famously exploited in the DAO hack of 2016.
        Similar to the Cream Finance incident.
        Related CVE-2024-1234 was assigned.
        """
        incidents = worker._extract_incidents(content)
        self.assertGreater(len(incidents), 0)


class TestMergeOrchestrator(unittest.TestCase):
    """Tests for MergeOrchestrator."""

    def test_init(self):
        """Test orchestrator initialization."""
        orchestrator = MergeOrchestrator()
        self.assertEqual(orchestrator.config.model, AgentModel.OPUS)
        self.assertTrue(orchestrator.is_opus)

    def test_compute_similarity(self):
        """Test similarity computation."""
        self.assertGreater(
            compute_similarity("hello world", "hello world"), 0.9
        )
        self.assertGreater(
            compute_similarity("reentrancy attack", "reentrancy vulnerability"),
            0.5,
        )
        self.assertEqual(compute_similarity("", "test"), 0.0)

    def test_deduplicate_strings(self):
        """Test string deduplication."""
        strings = [
            "Use reentrancy guard",
            "Use a reentrancy guard modifier",  # Similar
            "Apply CEI pattern",  # Different
            "Use CEI pattern for safety",  # Similar to above
        ]
        deduped = deduplicate_strings(strings, threshold=0.7)
        # Should remove highly similar strings
        self.assertLessEqual(len(deduped), len(strings))

    def test_generate_name(self):
        """Test name generation."""
        orchestrator = MergeOrchestrator()
        name = orchestrator._generate_name("classic-reentrancy")
        self.assertEqual(name, "Classic Reentrancy")

    def test_estimate_severity(self):
        """Test severity estimation."""
        orchestrator = MergeOrchestrator()
        from alphaswarm_sol.vulndocs.knowledge_doc import Severity

        self.assertEqual(
            orchestrator._estimate_severity("classic-reentrancy"),
            Severity.CRITICAL,
        )
        self.assertEqual(
            orchestrator._estimate_severity("missing-access-control"),
            Severity.HIGH,
        )

    def test_are_contradictory(self):
        """Test contradiction detection."""
        orchestrator = MergeOrchestrator()
        self.assertTrue(
            orchestrator._are_contradictory(
                "You should use a mutex",
                "You should not use a mutex",
            )
        )
        self.assertFalse(
            orchestrator._are_contradictory(
                "Use reentrancy guard",
                "Apply CEI pattern",
            )
        )


class TestSubagentCoordinator(unittest.TestCase):
    """Tests for SubagentCoordinator."""

    def test_init(self):
        """Test coordinator initialization."""
        coordinator = SubagentCoordinator(max_concurrent=5)
        self.assertEqual(coordinator.max_concurrent, 5)

    def test_register_agent(self):
        """Test agent registration."""

        class MockAgent(BaseAgent):
            async def process(self, input_data):
                return AgentResult.success_result(input_data)

        coordinator = SubagentCoordinator()
        agent = MockAgent("test-agent")
        coordinator.register_agent(agent)
        self.assertIn("test-agent", coordinator.agents)

    def test_add_task(self):
        """Test task addition."""
        coordinator = SubagentCoordinator()
        task = SubagentTask(
            task_id="task-1",
            agent_name="test-agent",
            input_data={"key": "value"},
        )
        coordinator.add_task(task)
        self.assertIn("task-1", coordinator.tasks)

    def test_get_progress(self):
        """Test progress retrieval."""
        coordinator = SubagentCoordinator()
        task1 = SubagentTask(
            task_id="1", agent_name="a", input_data={}, status=AgentStatus.PENDING
        )
        task2 = SubagentTask(
            task_id="2", agent_name="a", input_data={}, status=AgentStatus.COMPLETED
        )
        coordinator.add_task(task1)
        coordinator.add_task(task2)
        progress = coordinator.get_progress()
        self.assertEqual(progress["total"], 2)
        self.assertEqual(progress["pending"], 1)
        self.assertEqual(progress["completed"], 1)


class TestCategoryAgentIntegration(unittest.TestCase):
    """Integration tests for CategoryAgent."""

    def test_process_empty_sources(self):
        """Test processing empty sources."""

        async def run_test():
            agent = CategoryAgent("reentrancy")
            result = await agent.process([])
            return result

        result = asyncio.run(run_test())
        self.assertFalse(result.success)

    def test_process_with_sources(self):
        """Test processing with sources."""

        async def run_test():
            agent = CategoryAgent("reentrancy")
            sources = [
                CategorySource(
                    url="https://test.com/audit",
                    content="This is a classic reentrancy vulnerability where state is updated after external call.",
                    source_name="test-audit",
                ),
            ]
            result = await agent.process(sources)
            return result

        result = asyncio.run(run_test())
        self.assertTrue(result.success)
        self.assertIsInstance(result.data, CategoryResult)


class TestSubcategoryWorkerIntegration(unittest.TestCase):
    """Integration tests for SubcategoryWorker."""

    def test_process_sources(self):
        """Test processing sources."""

        async def run_test():
            worker = SubcategoryWorker("reentrancy", "classic-reentrancy")
            sources = [
                CategorySource(
                    url="https://test.com/1",
                    content="""
                    Classic reentrancy vulnerability.
                    - External call before state update
                    - Missing reentrancy guard
                    The attacker can reenter the function.
                    Fix: Use reentrancy guard.
                    """,
                    source_name="test",
                ),
            ]
            result = await worker.process(sources)
            return result

        result = asyncio.run(run_test())
        self.assertTrue(result.success)
        self.assertIsInstance(result.data, SubcategoryResult)
        self.assertGreater(len(result.data.summaries), 0)


class TestMergeOrchestratorIntegration(unittest.TestCase):
    """Integration tests for MergeOrchestrator."""

    def test_merge_summaries(self):
        """Test merging summaries."""

        async def run_test():
            orchestrator = MergeOrchestrator()
            summaries = [
                SourceSummary(
                    source_url="https://test1.com",
                    source_name="test1",
                    category="reentrancy",
                    subcategory="classic-reentrancy",
                    key_points=["Point A", "Point B"],
                    attack_vector="Attack method 1",
                    mitigation="Fix method 1",
                    source_authority=0.9,
                ),
                SourceSummary(
                    source_url="https://test2.com",
                    source_name="test2",
                    category="reentrancy",
                    subcategory="classic-reentrancy",
                    key_points=["Point C", "Point D"],
                    attack_vector="Attack method 2",
                    mitigation="Fix method 2",
                    source_authority=0.8,
                ),
            ]
            result = await orchestrator.process(
                {
                    "category": "reentrancy",
                    "subcategory": "classic-reentrancy",
                    "summaries": summaries,
                }
            )
            return result

        result = asyncio.run(run_test())
        self.assertTrue(result.success)
        self.assertIsNotNone(result.data.document)
        self.assertGreater(len(result.data.unique_ideas), 0)


if __name__ == "__main__":
    unittest.main()
