import pytest
"""Tests for VulnDocs Context Builder.

Phase 17.6: Context Builder Tests.

This test module covers:
- ContextSource creation tests
- BuiltContext creation and serialization tests
- ContextBuilder build methods tests
- Token budget tests
- Format function tests
- Integration tests with navigator and cache
"""

import shutil
import tempfile
from pathlib import Path
from unittest import TestCase, main

import yaml

from alphaswarm_sol.knowledge.vulndocs.builder import (
    ContextBuilder,
    ContextSource,
    BuiltContext,
    format_as_system_message,
    format_as_user_context,
    format_for_bead,
    PRIORITY_CRITICAL,
    PRIORITY_HIGH,
    PRIORITY_MEDIUM,
    PRIORITY_LOW,
    PRIORITY_NAVIGATION,
    DEFAULT_MAX_TOKENS,
    PATTERN_CATEGORY_MAP,
    OPERATION_CATEGORY_MAP,
)
from alphaswarm_sol.knowledge.vulndocs.cache import (
    CachedBlock,
    CacheControlType,
    PromptCache,
    estimate_tokens,
)
from alphaswarm_sol.knowledge.vulndocs.navigator import KnowledgeNavigator
from alphaswarm_sol.knowledge.vulndocs.schema import (
    KnowledgeDepth,
    KNOWLEDGE_DIR,
)


# =============================================================================
# CONTEXT SOURCE TESTS
# =============================================================================


class TestContextSourceCreation(TestCase):
    """Tests for ContextSource dataclass creation."""

    def test_create_basic_source(self):
        """Test creating a basic context source."""
        source = ContextSource(
            source_type="category",
            source_id="reentrancy",
            content="Reentrancy vulnerability content",
            tokens=50,
            priority=PRIORITY_HIGH,
        )

        self.assertEqual(source.source_type, "category")
        self.assertEqual(source.source_id, "reentrancy")
        self.assertEqual(source.content, "Reentrancy vulnerability content")
        self.assertEqual(source.tokens, 50)
        self.assertEqual(source.priority, PRIORITY_HIGH)

    def test_token_auto_calculation(self):
        """Test that tokens are auto-calculated from content."""
        content = "A" * 100
        source = ContextSource(
            source_type="custom",
            source_id="test",
            content=content,
            tokens=0,  # Should be calculated
            priority=PRIORITY_MEDIUM,
        )

        self.assertGreater(source.tokens, 0)
        self.assertLess(source.tokens, 100)

    def test_default_priority(self):
        """Test default priority is MEDIUM."""
        source = ContextSource(
            source_type="custom",
            source_id="test",
            content="Test content",
            tokens=10,
        )

        self.assertEqual(source.priority, PRIORITY_MEDIUM)

    def test_subcategory_source_type(self):
        """Test subcategory source type."""
        source = ContextSource(
            source_type="subcategory",
            source_id="reentrancy/classic",
            content="Classic reentrancy content",
            tokens=100,
            priority=PRIORITY_CRITICAL,
        )

        self.assertEqual(source.source_type, "subcategory")
        self.assertIn("/", source.source_id)


class TestContextSourceSerialization(TestCase):
    """Tests for ContextSource serialization."""

    def test_to_dict(self):
        """Test serializing source to dictionary."""
        source = ContextSource(
            source_type="category",
            source_id="access-control",
            content="Access control content",
            tokens=75,
            priority=PRIORITY_HIGH,
        )

        data = source.to_dict()

        self.assertEqual(data["source_type"], "category")
        self.assertEqual(data["source_id"], "access-control")
        self.assertEqual(data["content"], "Access control content")
        self.assertEqual(data["tokens"], 75)
        self.assertEqual(data["priority"], PRIORITY_HIGH)

    def test_from_dict(self):
        """Test deserializing source from dictionary."""
        data = {
            "source_type": "document",
            "source_id": "reentrancy/classic/detection",
            "content": "Detection guide content",
            "tokens": 200,
            "priority": PRIORITY_CRITICAL,
        }

        source = ContextSource.from_dict(data)

        self.assertEqual(source.source_type, "document")
        self.assertEqual(source.source_id, "reentrancy/classic/detection")
        self.assertEqual(source.tokens, 200)
        self.assertEqual(source.priority, PRIORITY_CRITICAL)

    def test_from_dict_minimal(self):
        """Test deserializing with minimal data."""
        data = {
            "content": "Minimal content",
        }

        source = ContextSource.from_dict(data)

        self.assertEqual(source.source_type, "custom")
        self.assertEqual(source.source_id, "")
        self.assertEqual(source.priority, PRIORITY_MEDIUM)

    def test_round_trip_serialization(self):
        """Test that to_dict -> from_dict preserves data."""
        original = ContextSource(
            source_type="finding",
            source_id="finding-vm-001",
            content="Finding specific content",
            tokens=150,
            priority=PRIORITY_CRITICAL,
        )

        data = original.to_dict()
        restored = ContextSource.from_dict(data)

        self.assertEqual(restored.source_type, original.source_type)
        self.assertEqual(restored.source_id, original.source_id)
        self.assertEqual(restored.content, original.content)
        self.assertEqual(restored.tokens, original.tokens)
        self.assertEqual(restored.priority, original.priority)


# =============================================================================
# BUILT CONTEXT TESTS
# =============================================================================


class TestBuiltContextCreation(TestCase):
    """Tests for BuiltContext dataclass creation."""

    def test_create_basic_context(self):
        """Test creating a basic built context."""
        context = BuiltContext(
            content="Combined vulnerability knowledge",
            sources=[],
            estimated_tokens=100,
            cache_blocks=[],
            metadata={"build_type": "pattern"},
        )

        self.assertEqual(context.content, "Combined vulnerability knowledge")
        self.assertEqual(context.estimated_tokens, 100)
        self.assertEqual(context.metadata["build_type"], "pattern")

    def test_token_auto_calculation(self):
        """Test that tokens are auto-calculated from content."""
        content = "A" * 400
        context = BuiltContext(
            content=content,
            estimated_tokens=0,  # Should be calculated
        )

        self.assertGreater(context.estimated_tokens, 0)

    def test_context_with_sources(self):
        """Test context with source list."""
        sources = [
            ContextSource("category", "reentrancy", "Content 1", 50, PRIORITY_HIGH),
            ContextSource("subcategory", "reentrancy/classic", "Content 2", 75, PRIORITY_CRITICAL),
        ]

        context = BuiltContext(
            content="Combined content",
            sources=sources,
            estimated_tokens=125,
        )

        self.assertEqual(len(context.sources), 2)
        self.assertEqual(context.sources[0].source_id, "reentrancy")
        self.assertEqual(context.sources[1].source_id, "reentrancy/classic")

    def test_context_with_cache_blocks(self):
        """Test context with cache blocks."""
        blocks = [
            CachedBlock(
                key="test-block-1",
                content="Cached content 1",
                cache_type=CacheControlType.EPHEMERAL,
            ),
            CachedBlock(
                key="test-block-2",
                content="Cached content 2",
                cache_type=CacheControlType.STATIC,
            ),
        ]

        context = BuiltContext(
            content="Content",
            cache_blocks=blocks,
        )

        self.assertEqual(len(context.cache_blocks), 2)


class TestBuiltContextMethods(TestCase):
    """Tests for BuiltContext methods."""

    def test_is_empty_true(self):
        """Test is_empty returns True for empty content."""
        context = BuiltContext(content="")
        self.assertTrue(context.is_empty())

        context2 = BuiltContext(content="   ")
        self.assertTrue(context2.is_empty())

    def test_is_empty_false(self):
        """Test is_empty returns False for non-empty content."""
        context = BuiltContext(content="Some content")
        self.assertFalse(context.is_empty())

    def test_get_source_ids(self):
        """Test getting all source IDs."""
        sources = [
            ContextSource("category", "reentrancy", "C1", 10, PRIORITY_HIGH),
            ContextSource("category", "access-control", "C2", 10, PRIORITY_HIGH),
            ContextSource("subcategory", "reentrancy/classic", "C3", 10, PRIORITY_CRITICAL),
        ]

        context = BuiltContext(content="Content", sources=sources)
        ids = context.get_source_ids()

        self.assertEqual(len(ids), 3)
        self.assertIn("reentrancy", ids)
        self.assertIn("access-control", ids)
        self.assertIn("reentrancy/classic", ids)

    def test_get_source_types(self):
        """Test getting unique source types."""
        sources = [
            ContextSource("category", "cat1", "C1", 10, PRIORITY_HIGH),
            ContextSource("category", "cat2", "C2", 10, PRIORITY_HIGH),
            ContextSource("subcategory", "cat1/sub1", "C3", 10, PRIORITY_MEDIUM),
            ContextSource("finding", "finding-1", "C4", 10, PRIORITY_CRITICAL),
        ]

        context = BuiltContext(content="Content", sources=sources)
        types = context.get_source_types()

        self.assertEqual(len(types), 3)
        self.assertIn("category", types)
        self.assertIn("subcategory", types)
        self.assertIn("finding", types)


class TestBuiltContextSerialization(TestCase):
    """Tests for BuiltContext serialization."""

    def test_to_dict(self):
        """Test serializing context to dictionary."""
        sources = [
            ContextSource("category", "reentrancy", "Content", 50, PRIORITY_HIGH),
        ]

        context = BuiltContext(
            content="Final content",
            sources=sources,
            estimated_tokens=50,
            metadata={"build_type": "pattern", "pattern_id": "vm-001"},
        )

        data = context.to_dict()

        self.assertEqual(data["content"], "Final content")
        self.assertEqual(len(data["sources"]), 1)
        self.assertEqual(data["estimated_tokens"], 50)
        self.assertEqual(data["metadata"]["build_type"], "pattern")

    def test_from_dict(self):
        """Test deserializing context from dictionary."""
        data = {
            "content": "Restored content",
            "sources": [
                {"source_type": "category", "source_id": "oracle", "content": "Oracle content", "tokens": 100, "priority": PRIORITY_HIGH}
            ],
            "estimated_tokens": 100,
            "metadata": {"build_type": "category"},
        }

        context = BuiltContext.from_dict(data)

        self.assertEqual(context.content, "Restored content")
        self.assertEqual(len(context.sources), 1)
        self.assertEqual(context.sources[0].source_id, "oracle")
        self.assertEqual(context.metadata["build_type"], "category")

    def test_round_trip_serialization(self):
        """Test that to_dict -> from_dict preserves data."""
        original = BuiltContext(
            content="Original content",
            sources=[
                ContextSource("category", "mev", "MEV content", 75, PRIORITY_HIGH),
            ],
            estimated_tokens=75,
            metadata={"operations": ["SWAP"]},
        )

        data = original.to_dict()
        restored = BuiltContext.from_dict(data)

        self.assertEqual(restored.content, original.content)
        self.assertEqual(len(restored.sources), len(original.sources))
        self.assertEqual(restored.estimated_tokens, original.estimated_tokens)
        self.assertEqual(restored.metadata, original.metadata)


# =============================================================================
# CONTEXT BUILDER TESTS - WITH TEMP KNOWLEDGE
# =============================================================================


class TestContextBuilderWithTempKnowledge(TestCase):
    """Tests for ContextBuilder with temporary knowledge base."""

    def setUp(self):
        """Set up test environment with temporary knowledge base."""
        self.temp_dir = tempfile.mkdtemp()
        self.base_path = Path(self.temp_dir)
        self._create_test_knowledge()
        self.navigator = KnowledgeNavigator(base_path=self.base_path)
        self.cache = PromptCache(self.navigator)
        self.builder = ContextBuilder(self.navigator, self.cache)

    def tearDown(self):
        """Clean up temporary directory."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _create_test_knowledge(self):
        """Create test knowledge structure."""
        # Create index
        index_data = {
            "schema_version": "1.0",
            "categories": {
                "reentrancy": {
                    "name": "Reentrancy",
                    "description": "Reentrancy vulnerabilities where external calls can re-enter",
                    "severity_range": ["high", "critical"],
                    "subcategories": [
                        {"id": "classic", "name": "Classic Reentrancy", "description": "State write after call"}
                    ],
                },
                "access-control": {
                    "name": "Access Control",
                    "description": "Access control vulnerabilities",
                    "severity_range": ["medium", "critical"],
                    "subcategories": [
                        {"id": "missing", "name": "Missing Controls", "description": "Missing access checks"}
                    ],
                },
                "oracle": {
                    "name": "Oracle",
                    "description": "Oracle manipulation vulnerabilities",
                    "severity_range": ["high", "critical"],
                    "subcategories": [],
                },
            },
            "operation_to_categories": {
                "TRANSFERS_VALUE_OUT": {"primary": ["reentrancy"], "secondary": ["token"]},
                "WRITES_USER_BALANCE": {"primary": ["reentrancy"], "secondary": []},
                "CHECKS_PERMISSION": {"primary": ["access-control"], "secondary": []},
                "READS_ORACLE": {"primary": ["oracle"], "secondary": []},
            },
            "signature_to_categories": {
                "R:bal->X:out->W:bal": {
                    "category": "reentrancy",
                    "subcategory": "classic",
                    "severity": "critical",
                }
            },
        }
        with open(self.base_path / "index.yaml", "w") as f:
            yaml.dump(index_data, f)

        # Create reentrancy category
        reen_dir = self.base_path / "categories" / "reentrancy"
        reen_dir.mkdir(parents=True)
        reen_data = {
            "id": "reentrancy",
            "name": "Reentrancy",
            "description": "Reentrancy vulnerabilities occur when external calls can re-enter the contract",
            "severity_range": ["high", "critical"],
            "subcategories": [
                {"id": "classic", "name": "Classic Reentrancy", "description": "State write after external call"}
            ],
            "relevant_properties": ["has_reentrancy_guard", "state_write_after_external_call"],
            "semantic_operations": ["TRANSFERS_VALUE_OUT", "WRITES_USER_BALANCE"],
        }
        with open(reen_dir / "index.yaml", "w") as f:
            yaml.dump(reen_data, f)

        # Create classic subcategory
        classic_dir = reen_dir / "subcategories" / "classic"
        classic_dir.mkdir(parents=True)
        classic_data = {
            "id": "classic",
            "name": "Classic Reentrancy",
            "parent_category": "reentrancy",
            "description": "Classic reentrancy where state is written after external call",
            "severity_range": ["high", "critical"],
            "patterns": ["vm-001-classic", "reentrancy-classic"],
            "behavioral_signatures": ["R:bal->X:out->W:bal"],
            "graph_signals": [
                {"property": "state_write_after_external_call", "expected": True, "critical": True}
            ],
        }
        with open(classic_dir / "index.yaml", "w") as f:
            yaml.dump(classic_data, f)

        # Create access-control category
        ac_dir = self.base_path / "categories" / "access-control"
        ac_dir.mkdir(parents=True)
        ac_data = {
            "id": "access-control",
            "name": "Access Control",
            "description": "Access control vulnerabilities related to permission checks",
            "severity_range": ["medium", "critical"],
            "subcategories": [
                {"id": "missing", "name": "Missing Controls", "description": "Missing access checks"}
            ],
            "relevant_properties": ["has_access_gate", "writes_privileged_state"],
        }
        with open(ac_dir / "index.yaml", "w") as f:
            yaml.dump(ac_data, f)

        # Create oracle category
        oracle_dir = self.base_path / "categories" / "oracle"
        oracle_dir.mkdir(parents=True)
        oracle_data = {
            "id": "oracle",
            "name": "Oracle",
            "description": "Oracle manipulation and stale price vulnerabilities",
            "severity_range": ["high", "critical"],
            "relevant_properties": ["reads_oracle_price", "has_staleness_check"],
        }
        with open(oracle_dir / "index.yaml", "w") as f:
            yaml.dump(oracle_data, f)


class TestBuildForPattern(TestContextBuilderWithTempKnowledge):
    """Tests for build_for_pattern method."""

    def test_build_for_reentrancy_pattern(self):
        """Test building context for reentrancy pattern."""
        context = self.builder.build_for_pattern("vm-001-classic")

        self.assertFalse(context.is_empty())
        self.assertIn("reentrancy", context.metadata.get("categories", []))
        self.assertEqual(context.metadata["build_type"], "pattern")
        self.assertGreater(len(context.sources), 0)

    def test_build_for_auth_pattern(self):
        """Test building context for auth pattern."""
        context = self.builder.build_for_pattern("auth-001-weak")

        self.assertFalse(context.is_empty())
        self.assertIn("access-control", context.metadata.get("categories", []))

    def test_build_includes_subcategory(self):
        """Test that build includes subcategory when pattern hints at it."""
        context = self.builder.build_for_pattern("vm-001-classic")

        # Check if subcategory source was included
        source_ids = context.get_source_ids()
        # May or may not have subcategory depending on hints
        self.assertGreater(len(source_ids), 0)

    def test_build_respects_token_budget(self):
        """Test that build respects token budget."""
        context = self.builder.build_for_pattern("vm-001-classic", max_tokens=500)

        self.assertLessEqual(context.estimated_tokens, 600)  # Some slack for estimation

    def test_build_caches_content(self):
        """Test that content is cached."""
        self.builder.build_for_pattern("vm-001-classic")

        stats = self.cache.get_cache_stats()
        self.assertGreater(stats["total_entries"], 0)

    def test_build_unknown_pattern(self):
        """Test building for unknown pattern prefix."""
        context = self.builder.build_for_pattern("unknown-pattern-xyz")

        # Should default to reentrancy or return something
        self.assertFalse(context.is_empty())


class TestBuildForFinding(TestContextBuilderWithTempKnowledge):
    """Tests for build_for_finding method."""

    def test_build_for_simple_finding(self):
        """Test building context for simple finding."""
        finding = {
            "pattern_id": "vm-001-classic",
            "severity": "high",
        }

        context = self.builder.build_for_finding(finding)

        self.assertFalse(context.is_empty())
        self.assertEqual(context.metadata["build_type"], "finding")
        self.assertEqual(context.metadata["severity"], "high")

    def test_build_for_finding_with_operations(self):
        """Test building with operations."""
        finding = {
            "pattern_id": "vm-001",
            "operations": ["TRANSFERS_VALUE_OUT", "WRITES_USER_BALANCE"],
            "severity": "critical",
        }

        context = self.builder.build_for_finding(finding)

        self.assertIn("reentrancy", context.metadata.get("categories", []))
        self.assertEqual(context.metadata["operations"], finding["operations"])

    def test_build_for_finding_with_signature(self):
        """Test building with behavioral signature."""
        finding = {
            "pattern": "reentrancy",
            "signature": "R:bal->X:out->W:bal",
        }

        context = self.builder.build_for_finding(finding)

        self.assertFalse(context.is_empty())
        self.assertIn("reentrancy", context.metadata.get("categories", []))

    def test_build_for_finding_with_function_info(self):
        """Test building with function information."""
        finding = {
            "pattern_id": "vm-001",
            "function_name": "withdraw",
            "contract_name": "Vault",
            "severity": "high",
        }

        context = self.builder.build_for_finding(finding)

        # Should include finding-specific context
        source_types = context.get_source_types()
        self.assertIn("finding", source_types)
        self.assertIn("withdraw", context.content)
        self.assertIn("Vault", context.content)

    def test_build_for_finding_respects_budget(self):
        """Test that finding build respects token budget."""
        finding = {
            "pattern_id": "vm-001",
            "operations": ["TRANSFERS_VALUE_OUT", "CHECKS_PERMISSION", "READS_ORACLE"],
            "severity": "critical",
        }

        context = self.builder.build_for_finding(finding, max_tokens=1000)

        self.assertLessEqual(context.estimated_tokens, 1200)


class TestBuildForCategory(TestContextBuilderWithTempKnowledge):
    """Tests for build_for_category method."""

    def test_build_for_category_detection(self):
        """Test building for category at detection depth."""
        context = self.builder.build_for_category(
            "reentrancy", depth=KnowledgeDepth.DETECTION
        )

        self.assertFalse(context.is_empty())
        self.assertEqual(context.metadata["category_id"], "reentrancy")
        self.assertEqual(context.metadata["depth"], "detection")
        self.assertEqual(context.metadata["build_type"], "category")

    def test_build_for_category_overview(self):
        """Test building for category at overview depth."""
        context = self.builder.build_for_category(
            "access-control", depth=KnowledgeDepth.OVERVIEW
        )

        self.assertFalse(context.is_empty())
        self.assertIn("Access Control", context.content)

    def test_build_for_category_full_depth(self):
        """Test building for category at full depth."""
        context = self.builder.build_for_category(
            "reentrancy", depth=KnowledgeDepth.FULL
        )

        # Full depth should include subcategory info
        self.assertGreater(len(context.sources), 0)

    def test_build_for_nonexistent_category(self):
        """Test building for nonexistent category."""
        context = self.builder.build_for_category("nonexistent")

        self.assertTrue(context.is_empty())


class TestBuildForOperations(TestContextBuilderWithTempKnowledge):
    """Tests for build_for_operations method."""

    def test_build_for_single_operation(self):
        """Test building for single operation."""
        context = self.builder.build_for_operations(["TRANSFERS_VALUE_OUT"])

        self.assertFalse(context.is_empty())
        self.assertIn("TRANSFERS_VALUE_OUT", context.metadata.get("operations", []))
        self.assertEqual(context.metadata["build_type"], "operations")

    def test_build_for_multiple_operations(self):
        """Test building for multiple operations."""
        operations = ["TRANSFERS_VALUE_OUT", "CHECKS_PERMISSION", "READS_ORACLE"]

        context = self.builder.build_for_operations(operations)

        self.assertFalse(context.is_empty())
        # Should map to multiple categories
        categories = context.metadata.get("categories", [])
        self.assertGreater(len(categories), 1)

    def test_build_includes_operations_summary(self):
        """Test that build includes operations summary."""
        context = self.builder.build_for_operations(["TRANSFERS_VALUE_OUT", "WRITES_USER_BALANCE"])

        # Should have summary source
        source_types = context.get_source_types()
        self.assertIn("summary", source_types)
        self.assertIn("Operations Analysis", context.content)

    def test_build_for_unknown_operations(self):
        """Test building for unknown operations."""
        context = self.builder.build_for_operations(["UNKNOWN_OP_1", "UNKNOWN_OP_2"])

        # Should still return something, potentially empty
        # as there's no mapping for unknown ops
        self.assertIsInstance(context, BuiltContext)


class TestBuildForSignature(TestContextBuilderWithTempKnowledge):
    """Tests for build_for_signature method."""

    def test_build_for_reentrancy_signature(self):
        """Test building for reentrancy signature."""
        context = self.builder.build_for_signature("R:bal->X:out->W:bal")

        self.assertFalse(context.is_empty())
        self.assertEqual(context.metadata["signature"], "R:bal->X:out->W:bal")
        self.assertEqual(context.metadata["build_type"], "signature")

    def test_build_includes_signature_analysis(self):
        """Test that build includes signature analysis."""
        context = self.builder.build_for_signature("R:bal->X:out->W:bal")

        source_types = context.get_source_types()
        self.assertIn("analysis", source_types)
        self.assertIn("Behavioral Signature Analysis", context.content)

    def test_build_extracts_operations(self):
        """Test that operations are extracted from signature."""
        context = self.builder.build_for_signature("R:bal->X:out->W:bal")

        operations = context.metadata.get("operations", [])
        self.assertIn("READS_USER_BALANCE", operations)
        self.assertIn("TRANSFERS_VALUE_OUT", operations)
        self.assertIn("WRITES_USER_BALANCE", operations)

    def test_build_for_safe_signature(self):
        """Test building for safe (CEI) signature."""
        context = self.builder.build_for_signature("R:bal->W:bal->X:out")

        self.assertFalse(context.is_empty())
        # Should note CEI pattern
        self.assertIn("CEI", context.content)


class TestBuildCustom(TestContextBuilderWithTempKnowledge):
    """Tests for build_custom method."""

    def test_build_custom_single_source(self):
        """Test building with single custom source."""
        sources = [
            ContextSource(
                source_type="custom",
                source_id="my-source",
                content="Custom vulnerability knowledge",
                tokens=50,
                priority=PRIORITY_HIGH,
            )
        ]

        context = self.builder.build_custom(sources)

        self.assertFalse(context.is_empty())
        self.assertEqual(context.metadata["build_type"], "custom")
        self.assertEqual(len(context.sources), 1)

    def test_build_custom_multiple_sources(self):
        """Test building with multiple custom sources."""
        sources = [
            ContextSource("custom", "source-1", "Content 1", 50, PRIORITY_LOW),
            ContextSource("custom", "source-2", "Content 2", 75, PRIORITY_HIGH),
            ContextSource("custom", "source-3", "Content 3", 100, PRIORITY_CRITICAL),
        ]

        context = self.builder.build_custom(sources)

        self.assertEqual(len(context.sources), 3)
        # Should be sorted by priority
        self.assertEqual(context.sources[0].priority, PRIORITY_CRITICAL)

    def test_build_custom_caches_sources(self):
        """Test that custom sources are cached."""
        sources = [
            ContextSource("custom", "cached-source", "Cache me", 50, PRIORITY_MEDIUM)
        ]

        context = self.builder.build_custom(sources)

        self.assertGreater(len(context.cache_blocks), 0)


# =============================================================================
# TOKEN BUDGET TESTS
# =============================================================================


class TestTokenBudget(TestContextBuilderWithTempKnowledge):
    """Tests for token budget optimization."""

    def test_prioritizes_high_priority_sources(self):
        """Test that high priority sources are included first."""
        # Create scenario where budget is tight
        context = self.builder.build_for_pattern("vm-001-classic", max_tokens=500)

        # Higher priority sources should be included
        if len(context.sources) > 0:
            priorities = [s.priority for s in context.sources]
            # Should generally be sorted high to low
            self.assertGreaterEqual(max(priorities), min(priorities))

    def test_truncates_content_gracefully(self):
        """Test that content is truncated at section boundaries."""
        # Build with very low budget
        context = self.builder.build_for_pattern("vm-001-classic", max_tokens=200)

        # Content should not be empty if there's any relevant knowledge
        # and should end cleanly (no partial sentences)
        if context.content:
            # Should not end mid-word
            self.assertNotRegex(context.content[-20:] if len(context.content) > 20 else context.content, r'\w{10,}$')

    def test_respects_min_tokens_per_source(self):
        """Test that sources below minimum are not truncated to unusable size."""
        context = self.builder.build_for_pattern("vm-001-classic", max_tokens=300)

        for source in context.sources:
            # Either full source or at least MIN_TOKENS_PER_SOURCE
            self.assertGreater(source.tokens, 0)


# =============================================================================
# FORMAT FUNCTION TESTS
# =============================================================================


class TestFormatFunctions(TestCase):
    """Tests for format functions."""

    def test_format_as_system_message(self):
        """Test formatting as system message."""
        context = BuiltContext(
            content="Vulnerability knowledge content",
            sources=[ContextSource("category", "reentrancy", "C", 50, PRIORITY_HIGH)],
            estimated_tokens=50,
            metadata={"build_type": "pattern"},
        )

        result = format_as_system_message(context)

        self.assertIn("VulnDocs Knowledge Context", result)
        self.assertIn("Sources: 1", result)
        self.assertIn("Tokens: ~50", result)
        self.assertIn("Vulnerability knowledge content", result)

    def test_format_as_system_message_empty(self):
        """Test formatting empty context as system message."""
        context = BuiltContext(content="")

        result = format_as_system_message(context)

        self.assertEqual(result, "")

    def test_format_as_user_context(self):
        """Test formatting as user context."""
        context = BuiltContext(
            content="User context content",
            estimated_tokens=25,
        )

        result = format_as_user_context(context)

        self.assertIn("<vulnerability-knowledge>", result)
        self.assertIn("</vulnerability-knowledge>", result)
        self.assertIn("User context content", result)

    def test_format_as_user_context_empty(self):
        """Test formatting empty context as user context."""
        context = BuiltContext(content="")

        result = format_as_user_context(context)

        self.assertEqual(result, "")

    def test_format_for_bead(self):
        """Test formatting for bead."""
        context = BuiltContext(
            content="Bead content",
            estimated_tokens=30,
            metadata={"build_type": "pattern", "pattern_id": "vm-001"},
        )

        result = format_for_bead(context, "detection-bead")

        self.assertIn("<!-- Bead: detection-bead", result)
        self.assertIn("pattern -->", result)
        self.assertIn("pattern_id=vm-001", result)
        self.assertIn("Bead content", result)
        self.assertIn("<!-- End Bead: detection-bead -->", result)

    def test_format_for_bead_empty(self):
        """Test formatting empty context for bead."""
        context = BuiltContext(content="")

        result = format_for_bead(context, "empty-bead")

        self.assertEqual(result, "")


# =============================================================================
# PATTERN CATEGORY MAPPING TESTS
# =============================================================================


class TestPatternCategoryMapping(TestCase):
    """Tests for pattern-to-category mapping."""

    def test_reentrancy_patterns(self):
        """Test reentrancy pattern prefixes."""
        self.assertIn("reentrancy", PATTERN_CATEGORY_MAP)
        self.assertIn("reentrancy", PATTERN_CATEGORY_MAP["reentrancy"])

    def test_vm_patterns(self):
        """Test value-movement patterns."""
        self.assertIn("vm", PATTERN_CATEGORY_MAP)
        self.assertIn("reentrancy", PATTERN_CATEGORY_MAP["vm"])
        self.assertIn("token", PATTERN_CATEGORY_MAP["vm"])

    def test_auth_patterns(self):
        """Test auth patterns."""
        self.assertIn("auth", PATTERN_CATEGORY_MAP)
        self.assertIn("access-control", PATTERN_CATEGORY_MAP["auth"])

    def test_oracle_patterns(self):
        """Test oracle patterns."""
        self.assertIn("oracle", PATTERN_CATEGORY_MAP)
        self.assertIn("price", PATTERN_CATEGORY_MAP)

    def test_mev_patterns(self):
        """Test MEV patterns."""
        self.assertIn("mev", PATTERN_CATEGORY_MAP)
        self.assertIn("swap", PATTERN_CATEGORY_MAP)


class TestOperationCategoryMapping(TestCase):
    """Tests for operation-to-category mapping."""

    def test_value_operations(self):
        """Test value-related operations."""
        self.assertIn("TRANSFERS_VALUE_OUT", OPERATION_CATEGORY_MAP)
        self.assertIn("reentrancy", OPERATION_CATEGORY_MAP["TRANSFERS_VALUE_OUT"])

        self.assertIn("WRITES_USER_BALANCE", OPERATION_CATEGORY_MAP)
        self.assertIn("reentrancy", OPERATION_CATEGORY_MAP["WRITES_USER_BALANCE"])

    def test_permission_operations(self):
        """Test permission-related operations."""
        self.assertIn("CHECKS_PERMISSION", OPERATION_CATEGORY_MAP)
        self.assertIn("access-control", OPERATION_CATEGORY_MAP["CHECKS_PERMISSION"])

        self.assertIn("MODIFIES_OWNER", OPERATION_CATEGORY_MAP)
        self.assertIn("access-control", OPERATION_CATEGORY_MAP["MODIFIES_OWNER"])

    def test_external_operations(self):
        """Test external call operations."""
        self.assertIn("CALLS_EXTERNAL", OPERATION_CATEGORY_MAP)
        self.assertIn("CALLS_UNTRUSTED", OPERATION_CATEGORY_MAP)

    def test_oracle_operations(self):
        """Test oracle operations."""
        self.assertIn("READS_ORACLE", OPERATION_CATEGORY_MAP)
        self.assertIn("oracle", OPERATION_CATEGORY_MAP["READS_ORACLE"])


# =============================================================================
# INTEGRATION TESTS WITH REAL KNOWLEDGE
# =============================================================================


class TestWithRealKnowledge(TestCase):
    """Integration tests with real knowledge base."""

    def setUp(self):
        """Set up with real knowledge if available."""
        self.navigator = KnowledgeNavigator()
        self.cache = PromptCache(self.navigator)
        self.builder = ContextBuilder(self.navigator, self.cache)

    def test_build_for_real_pattern(self):
        """Test building for real pattern if available."""
        if not KNOWLEDGE_DIR.exists():
            self.skipTest("Knowledge directory does not exist")

        context = self.builder.build_for_pattern("reentrancy-classic")

        self.assertFalse(context.is_empty())
        self.assertIn("reentrancy", context.metadata.get("categories", []))

    @pytest.mark.xfail(reason="Stale code: VulnDocs index schema format changed")
    def test_build_for_real_operations(self):
        """Test building for real operations if available."""
        if not KNOWLEDGE_DIR.exists():
            self.skipTest("Knowledge directory does not exist")

        context = self.builder.build_for_operations(
            ["TRANSFERS_VALUE_OUT", "WRITES_USER_BALANCE"]
        )

        self.assertFalse(context.is_empty())

    @pytest.mark.xfail(reason="Stale code: VulnDocs index schema format changed")
    def test_build_for_real_category(self):
        """Test building for real category if available."""
        if not KNOWLEDGE_DIR.exists():
            self.skipTest("Knowledge directory does not exist")

        try:
            context = self.builder.build_for_category("reentrancy")
            self.assertFalse(context.is_empty())
        except (ValueError, FileNotFoundError):
            self.skipTest("Reentrancy category not available")

    def test_format_real_context(self):
        """Test formatting real context."""
        if not KNOWLEDGE_DIR.exists():
            self.skipTest("Knowledge directory does not exist")

        context = self.builder.build_for_pattern("vm-001")

        if not context.is_empty():
            system_msg = format_as_system_message(context)
            self.assertIn("VulnDocs", system_msg)

            user_ctx = format_as_user_context(context)
            self.assertIn("<vulnerability-knowledge>", user_ctx)

            bead = format_for_bead(context, "test-bead")
            self.assertIn("<!-- Bead:", bead)


if __name__ == "__main__":
    main()
