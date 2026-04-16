"""Tests for VulnDocs Context Builder.

Task 18.21: Dynamic context assembly for LLM consumption.
"""

import unittest
from typing import Dict, Any, List

from alphaswarm_sol.vulndocs.context.builder import (
    ContextBuilder,
    ContextMode,
    ContextPriority,
    ContextSection,
    ContextConfig,
    BuiltContext,
    build_context_for_finding,
    build_navigation_context,
    get_builder,
    set_builder,
)
from alphaswarm_sol.vulndocs.context.cache import (
    CacheableContext,
    CacheLayer,
    CachedContextSet,
    PromptCacheManager,
    get_cache_manager,
    set_cache_manager,
)
from alphaswarm_sol.vulndocs.context.assembly import (
    ContextAssembler,
    AssemblyStrategy,
    ContentSource,
    AssembledContext,
    assemble_for_finding,
    quick_assemble,
)
from alphaswarm_sol.vulndocs.storage.retrieval import RetrievalDepth
from alphaswarm_sol.vulndocs.storage.knowledge_store import KnowledgeStore, StorageConfig
from alphaswarm_sol.vulndocs.knowledge_doc import (
    VulnKnowledgeDoc,
    Severity,
    DetectionSection,
    MitigationSection,
    ExploitationSection,
    ExamplesSection,
    PatternLinkage,
    PatternLinkageType,
    RealExploitRef,
)
from alphaswarm_sol.vulndocs.tools.formatters import OutputFormat


# =============================================================================
# Test Fixtures
# =============================================================================

def create_test_doc(
    doc_id: str = "reentrancy/classic/test-doc",
    category: str = "reentrancy",
    subcategory: str = "classic",
) -> VulnKnowledgeDoc:
    """Create a test document."""
    return VulnKnowledgeDoc(
        id=doc_id,
        name="Classic Reentrancy",
        category=category,
        subcategory=subcategory,
        severity=Severity.CRITICAL,
        one_liner="State update after external call enables callbacks",
        tldr="Classic reentrancy occurs when state is modified after external call.",
        detection=DetectionSection(
            graph_signals=["state_write_after_external_call", "no_reentrancy_guard"],
            vulnerable_sequence="R:bal→X:out→W:bal",
            indicators=["external call before state update"],
        ),
        mitigation=MitigationSection(
            primary_fix="Use CEI pattern",
            alternative_fixes=["Reentrancy guard", "Pull pattern"],
            safe_pattern="CEI",
            how_to_verify=["Check state update order", "Verify guard presence"],
        ),
        exploitation=ExploitationSection(
            attack_vector="Recursive call during external transfer",
            prerequisites=["External call to attacker", "State update after call"],
            attack_steps=["Deploy malicious contract", "Call vulnerable withdraw", "Re-enter in callback"],
        ),
        examples=ExamplesSection(
            vulnerable_code="balances[msg.sender] -= amount; msg.sender.call{value: amount}('')",
            fixed_code="balances[msg.sender] -= amount; _transfer(msg.sender, amount)",
            real_exploits=[
                RealExploitRef(
                    name="The DAO",
                    date="2016-06-17",
                    loss="$60M",
                    brief="Classic reentrancy exploit",
                ),
            ],
        ),
        pattern_linkage=PatternLinkage(
            pattern_ids=["reentrancy-001"],
            linkage_type=PatternLinkageType.EXACT_MATCH,
        ),
    )


# =============================================================================
# ContextSection Tests
# =============================================================================

class TestContextSection(unittest.TestCase):
    """Test ContextSection dataclass."""

    def test_section_creation(self):
        """Test basic section creation."""
        section = ContextSection(
            name="detection",
            content="Test detection content",
            priority=ContextPriority.CRITICAL,
        )

        self.assertEqual(section.name, "detection")
        self.assertEqual(section.priority, ContextPriority.CRITICAL)
        self.assertGreater(section.token_estimate, 0)

    def test_section_token_estimate(self):
        """Test automatic token estimation."""
        content = "x" * 400  # ~100 tokens at 4 chars/token
        section = ContextSection(
            name="test",
            content=content,
            priority=ContextPriority.HIGH,
        )

        self.assertEqual(section.token_estimate, 100)

    def test_section_explicit_tokens(self):
        """Test explicit token override."""
        section = ContextSection(
            name="test",
            content="short",
            priority=ContextPriority.HIGH,
            token_estimate=500,
        )

        self.assertEqual(section.token_estimate, 500)

    def test_section_to_dict(self):
        """Test serialization."""
        section = ContextSection(
            name="test",
            content="content",
            priority=ContextPriority.MEDIUM,
            cacheable=True,
            source="reentrancy",
        )

        data = section.to_dict()

        self.assertEqual(data["name"], "test")
        self.assertEqual(data["priority"], "MEDIUM")
        self.assertTrue(data["cacheable"])
        self.assertEqual(data["source"], "reentrancy")


class TestBuiltContext(unittest.TestCase):
    """Test BuiltContext dataclass."""

    def test_built_context_creation(self):
        """Test basic creation."""
        ctx = BuiltContext(
            content="Test content",
            mode=ContextMode.FINDING_ANALYSIS,
        )

        self.assertEqual(ctx.mode, ContextMode.FINDING_ANALYSIS)
        self.assertGreater(ctx.total_tokens, 0)

    def test_built_context_budget_used(self):
        """Test budget calculation."""
        section = ContextSection(
            name="test",
            content="x" * 400,  # 100 tokens
            priority=ContextPriority.HIGH,
        )

        ctx = BuiltContext(
            content="x" * 400,
            sections=[section],
            total_tokens=100,
            budget_used=0.25,  # 100/400
        )

        self.assertEqual(ctx.budget_used, 0.25)

    def test_get_cacheable_prefix(self):
        """Test extracting cacheable sections."""
        cacheable_section = ContextSection(
            name="system",
            content="System content",
            priority=ContextPriority.CRITICAL,
            cacheable=True,
        )
        dynamic_section = ContextSection(
            name="finding",
            content="Finding content",
            priority=ContextPriority.HIGH,
            cacheable=False,
        )

        ctx = BuiltContext(
            content="Combined",
            sections=[cacheable_section, dynamic_section],
        )

        prefix = ctx.get_cacheable_prefix()
        suffix = ctx.get_dynamic_suffix()

        self.assertEqual(prefix, "System content")
        self.assertEqual(suffix, "Finding content")

    def test_to_dict(self):
        """Test serialization."""
        ctx = BuiltContext(
            content="Test",
            mode=ContextMode.INVESTIGATION,
            truncated=True,
            excluded_sections=["exploits"],
        )

        data = ctx.to_dict()

        self.assertEqual(data["mode"], "INVESTIGATION")
        self.assertTrue(data["truncated"])
        self.assertIn("exploits", data["excluded_sections"])


# =============================================================================
# ContextBuilder Tests
# =============================================================================

class TestContextBuilder(unittest.TestCase):
    """Test ContextBuilder class."""

    def setUp(self):
        """Set up test fixtures."""
        # Create test store with document
        import tempfile
        self.temp_dir = tempfile.mkdtemp()
        config = StorageConfig(base_path=self.temp_dir)
        self.store = KnowledgeStore(config)
        self.doc = create_test_doc()
        self.store.save(self.doc)

        # Create retriever and builder
        from alphaswarm_sol.vulndocs.storage.retrieval import KnowledgeRetriever
        self.retriever = KnowledgeRetriever(store=self.store)
        self.builder = ContextBuilder(retriever=self.retriever)

    def tearDown(self):
        """Clean up."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_build_for_finding_basic(self):
        """Test building context for a finding."""
        finding = {
            "category": "reentrancy",
            "subcategory": "classic",
            "signals": ["state_write_after_external_call"],
        }

        ctx = self.builder.build_for_finding(finding)

        self.assertIsInstance(ctx, BuiltContext)
        self.assertGreater(len(ctx.content), 0)
        self.assertEqual(ctx.mode, ContextMode.FINDING_ANALYSIS)

    def test_build_for_finding_with_max_tokens(self):
        """Test token budget is respected."""
        finding = {"category": "reentrancy", "subcategory": "classic"}

        ctx = self.builder.build_for_finding(finding, max_tokens=500)

        self.assertLessEqual(ctx.total_tokens, 500)

    def test_build_for_finding_modes(self):
        """Test different context modes."""
        finding = {"category": "reentrancy"}

        # Test each mode
        modes = [
            ContextMode.FINDING_ANALYSIS,
            ContextMode.VERIFICATION,
            ContextMode.REMEDIATION,
            ContextMode.MINIMAL,
        ]

        for mode in modes:
            ctx = self.builder.build_for_finding(finding, mode=mode)
            self.assertEqual(ctx.mode, mode)

    def test_build_investigation(self):
        """Test multi-category investigation context."""
        ctx = self.builder.build_investigation(
            categories=["reentrancy"],
            max_tokens=2000,
        )

        self.assertEqual(ctx.mode, ContextMode.INVESTIGATION)
        self.assertGreater(len(ctx.content), 0)

    def test_build_navigation(self):
        """Test navigation context."""
        ctx = self.builder.build_navigation(max_tokens=1000)

        self.assertEqual(ctx.mode, ContextMode.NAVIGATION)
        # Should include tool guide
        self.assertIn("Available Tools", ctx.content)

    def test_build_verification(self):
        """Test verification context."""
        finding = {"category": "reentrancy"}

        ctx = self.builder.build_verification(finding)

        self.assertEqual(ctx.mode, ContextMode.VERIFICATION)

    def test_build_remediation(self):
        """Test remediation context."""
        finding = {"category": "reentrancy"}

        ctx = self.builder.build_remediation(finding)

        self.assertEqual(ctx.mode, ContextMode.REMEDIATION)

    def test_build_minimal(self):
        """Test minimal context."""
        finding = {"category": "reentrancy"}

        ctx = self.builder.build_minimal(finding, max_tokens=500)

        self.assertEqual(ctx.mode, ContextMode.MINIMAL)
        self.assertLessEqual(ctx.total_tokens, 500)

    def test_expand_context(self):
        """Test context expansion."""
        finding = {"category": "reentrancy"}

        # Build initial context
        initial = self.builder.build_minimal(finding, max_tokens=500)
        initial_tokens = initial.total_tokens

        # Expand
        expanded = self.builder.expand_context(
            current=initial,
            finding=finding,
            expand_sections=["exploits"],
            additional_tokens=500,
        )

        # Should have more content
        self.assertGreaterEqual(expanded.total_tokens, initial_tokens)

    def test_config_output_format(self):
        """Test output format configuration."""
        config = ContextConfig(output_format=OutputFormat.TOON)
        builder = ContextBuilder(retriever=self.retriever, config=config)

        finding = {"category": "reentrancy"}
        ctx = builder.build_for_finding(finding)

        # TOON format uses special characters
        # Content should exist even if format details vary
        self.assertIsInstance(ctx.content, str)


class TestContextBuilderConvenience(unittest.TestCase):
    """Test convenience functions."""

    def test_get_set_builder(self):
        """Test default builder management."""
        original = get_builder()
        new_builder = ContextBuilder()

        set_builder(new_builder)
        self.assertIs(get_builder(), new_builder)

        # Restore
        set_builder(original)

    def test_build_context_for_finding_function(self):
        """Test convenience function."""
        finding = {"category": "test"}

        # Should not raise
        ctx = build_context_for_finding(finding, max_tokens=500)
        self.assertIsInstance(ctx, BuiltContext)

    def test_build_navigation_context_function(self):
        """Test navigation convenience function."""
        ctx = build_navigation_context(max_tokens=1000)
        self.assertIsInstance(ctx, BuiltContext)


# =============================================================================
# CacheableContext Tests
# =============================================================================

class TestCacheableContext(unittest.TestCase):
    """Test CacheableContext class."""

    def test_cacheable_context_creation(self):
        """Test basic creation."""
        ctx = CacheableContext(
            content="Test system content",
            layer=CacheLayer.SYSTEM,
        )

        self.assertEqual(ctx.layer, CacheLayer.SYSTEM)
        self.assertGreater(len(ctx.cache_key), 0)
        self.assertGreater(ctx.token_estimate, 0)

    def test_cache_key_generation(self):
        """Test cache key is generated from content hash."""
        ctx1 = CacheableContext(content="content A", layer=CacheLayer.SYSTEM)
        ctx2 = CacheableContext(content="content A", layer=CacheLayer.SYSTEM)
        ctx3 = CacheableContext(content="content B", layer=CacheLayer.SYSTEM)

        # Same content = same key
        self.assertEqual(ctx1.cache_key, ctx2.cache_key)
        # Different content = different key
        self.assertNotEqual(ctx1.cache_key, ctx3.cache_key)

    def test_to_anthropic_block(self):
        """Test Anthropic API block generation."""
        # Cacheable layer
        system_ctx = CacheableContext(
            content="System instructions",
            layer=CacheLayer.SYSTEM,
        )

        block = system_ctx.to_anthropic_block()

        self.assertEqual(block["type"], "text")
        self.assertEqual(block["text"], "System instructions")
        self.assertIn("cache_control", block)
        self.assertEqual(block["cache_control"]["type"], "ephemeral")

    def test_dynamic_no_cache_control(self):
        """Test dynamic layer has no cache control."""
        dynamic_ctx = CacheableContext(
            content="Finding-specific content",
            layer=CacheLayer.DYNAMIC,
        )

        block = dynamic_ctx.to_anthropic_block()

        self.assertNotIn("cache_control", block)

    def test_to_dict(self):
        """Test serialization."""
        ctx = CacheableContext(
            content="Test",
            layer=CacheLayer.CATEGORY,
            version="1.0",
            source="reentrancy",
        )

        data = ctx.to_dict()

        self.assertEqual(data["layer"], "category")
        self.assertEqual(data["version"], "1.0")
        self.assertEqual(data["source"], "reentrancy")


class TestCachedContextSet(unittest.TestCase):
    """Test CachedContextSet class."""

    def test_empty_set(self):
        """Test empty context set."""
        ctx_set = CachedContextSet()

        self.assertIsNone(ctx_set.system_context)
        self.assertEqual(len(ctx_set.category_contexts), 0)
        self.assertIsNone(ctx_set.dynamic_context)
        self.assertEqual(ctx_set.get_total_tokens(), 0)

    def test_full_set(self):
        """Test fully populated context set."""
        ctx_set = CachedContextSet(
            system_context=CacheableContext(
                content="System",
                layer=CacheLayer.SYSTEM,
            ),
            category_contexts=[
                CacheableContext(
                    content="Category 1",
                    layer=CacheLayer.CATEGORY,
                ),
            ],
            dynamic_context=CacheableContext(
                content="Dynamic",
                layer=CacheLayer.DYNAMIC,
            ),
        )

        self.assertGreater(ctx_set.get_total_tokens(), 0)

    def test_to_anthropic_blocks(self):
        """Test Anthropic blocks generation in correct order."""
        ctx_set = CachedContextSet(
            system_context=CacheableContext(content="1", layer=CacheLayer.SYSTEM),
            category_contexts=[
                CacheableContext(content="2", layer=CacheLayer.CATEGORY),
            ],
            dynamic_context=CacheableContext(content="3", layer=CacheLayer.DYNAMIC),
        )

        blocks = ctx_set.to_anthropic_blocks()

        self.assertEqual(len(blocks), 3)
        # Check order: system, category, dynamic
        self.assertEqual(blocks[0]["text"], "1")
        self.assertEqual(blocks[1]["text"], "2")
        self.assertEqual(blocks[2]["text"], "3")

    def test_get_combined_content(self):
        """Test combined content string."""
        ctx_set = CachedContextSet(
            system_context=CacheableContext(content="A", layer=CacheLayer.SYSTEM),
            category_contexts=[
                CacheableContext(content="B", layer=CacheLayer.CATEGORY),
            ],
            dynamic_context=CacheableContext(content="C", layer=CacheLayer.DYNAMIC),
        )

        combined = ctx_set.get_combined_content()

        self.assertIn("A", combined)
        self.assertIn("B", combined)
        self.assertIn("C", combined)


# =============================================================================
# PromptCacheManager Tests
# =============================================================================

class TestPromptCacheManager(unittest.TestCase):
    """Test PromptCacheManager class."""

    def test_manager_creation(self):
        """Test basic creation."""
        manager = PromptCacheManager(version="1.0")

        self.assertEqual(manager.version, "1.0")
        self.assertIsNone(manager.get_system_context())

    def test_set_system_context(self):
        """Test setting system context."""
        manager = PromptCacheManager()

        ctx = manager.set_system_context("Navigation instructions")

        self.assertEqual(ctx.layer, CacheLayer.SYSTEM)
        self.assertEqual(manager.get_system_context().content, "Navigation instructions")

    def test_set_category_context(self):
        """Test setting category context."""
        manager = PromptCacheManager()

        ctx = manager.set_category_context("reentrancy", "Reentrancy overview")

        self.assertEqual(ctx.layer, CacheLayer.CATEGORY)
        self.assertEqual(ctx.source, "reentrancy")

        retrieved = manager.get_category_context("reentrancy")
        self.assertEqual(retrieved.content, "Reentrancy overview")

    def test_create_dynamic_context(self):
        """Test creating dynamic context."""
        manager = PromptCacheManager()

        ctx = manager.create_dynamic_context("Finding details", source="finding-001")

        self.assertEqual(ctx.layer, CacheLayer.DYNAMIC)
        self.assertEqual(ctx.source, "finding-001")

    def test_build_context_set(self):
        """Test building full context set."""
        manager = PromptCacheManager()
        manager.set_system_context("System")
        manager.set_category_context("reentrancy", "Reentrancy")

        ctx_set = manager.build_context_set(
            categories=["reentrancy"],
            dynamic_content="Finding X",
        )

        self.assertIsNotNone(ctx_set.system_context)
        self.assertEqual(len(ctx_set.category_contexts), 1)
        self.assertIsNotNone(ctx_set.dynamic_context)

    def test_build_context_set_without_system(self):
        """Test building context set without system context."""
        manager = PromptCacheManager()

        ctx_set = manager.build_context_set(
            dynamic_content="Just finding",
            include_system=False,
        )

        self.assertIsNone(ctx_set.system_context)
        self.assertIsNotNone(ctx_set.dynamic_context)

    def test_invalidate_category(self):
        """Test category cache invalidation."""
        manager = PromptCacheManager()
        manager.set_category_context("reentrancy", "Content")

        self.assertIsNotNone(manager.get_category_context("reentrancy"))

        result = manager.invalidate_category("reentrancy")

        self.assertTrue(result)
        self.assertIsNone(manager.get_category_context("reentrancy"))

    def test_invalidate_all(self):
        """Test full cache invalidation."""
        manager = PromptCacheManager()
        manager.set_system_context("System")
        manager.set_category_context("cat1", "Cat1")
        manager.set_category_context("cat2", "Cat2")

        manager.invalidate_all()

        self.assertIsNone(manager.get_system_context())
        self.assertIsNone(manager.get_category_context("cat1"))
        self.assertIsNone(manager.get_category_context("cat2"))

    def test_get_cache_stats(self):
        """Test cache statistics."""
        manager = PromptCacheManager(version="2.0")
        manager.set_system_context("System content here")
        manager.set_category_context("reentrancy", "Reentrancy docs")

        stats = manager.get_cache_stats()

        self.assertTrue(stats["has_system_cache"])
        self.assertGreater(stats["system_tokens"], 0)
        self.assertEqual(stats["category_count"], 1)
        self.assertIn("reentrancy", stats["categories_cached"])
        self.assertEqual(stats["version"], "2.0")

    def test_estimate_cache_savings(self):
        """Test cache savings estimation."""
        manager = PromptCacheManager()
        manager.set_system_context("x" * 1200)  # ~300 tokens

        ctx_set = manager.build_context_set(
            dynamic_content="y" * 400,  # ~100 tokens
        )

        savings = manager.estimate_cache_savings(ctx_set, calls_per_session=10)

        self.assertGreater(savings["cacheable_tokens"], 0)
        self.assertGreater(savings["uncacheable_tokens"], 0)
        self.assertGreater(savings["savings_percent"], 0)

    def test_convenience_functions(self):
        """Test get/set cache manager functions."""
        original = get_cache_manager()
        new_manager = PromptCacheManager(version="test")

        set_cache_manager(new_manager)
        self.assertEqual(get_cache_manager().version, "test")

        # Restore
        set_cache_manager(original)


# =============================================================================
# ContentSource Tests
# =============================================================================

class TestContentSource(unittest.TestCase):
    """Test ContentSource class."""

    def test_source_creation(self):
        """Test basic creation."""
        source = ContentSource(
            source_id="detection",
            content="Detection guidance",
            priority=1,
        )

        self.assertEqual(source.source_id, "detection")
        self.assertEqual(source.priority, 1)
        self.assertGreater(source.token_estimate, 0)

    def test_source_auto_token_estimate(self):
        """Test automatic token estimation."""
        content = "x" * 400  # ~100 tokens
        source = ContentSource(
            source_id="test",
            content=content,
        )

        self.assertEqual(source.token_estimate, 100)

    def test_source_with_metadata(self):
        """Test source with metadata."""
        source = ContentSource(
            source_id="test",
            content="Content",
            category="reentrancy",
            metadata={"key": "value"},
        )

        self.assertEqual(source.category, "reentrancy")
        self.assertEqual(source.metadata["key"], "value")


# =============================================================================
# ContextAssembler Tests
# =============================================================================

class TestContextAssembler(unittest.TestCase):
    """Test ContextAssembler class."""

    def test_assembler_creation(self):
        """Test basic creation."""
        assembler = ContextAssembler()

        self.assertEqual(len(assembler.sources), 0)

    def test_add_source(self):
        """Test adding sources."""
        assembler = ContextAssembler()

        assembler.add_source(
            ContentSource(source_id="a", content="A", priority=1)
        )

        self.assertEqual(len(assembler.sources), 1)

    def test_add_sources_chain(self):
        """Test chaining add methods."""
        assembler = ContextAssembler()

        result = (
            assembler
            .add_source(ContentSource(source_id="a", content="A"))
            .add_source(ContentSource(source_id="b", content="B"))
        )

        self.assertIs(result, assembler)
        self.assertEqual(len(assembler.sources), 2)

    def test_add_sources_batch(self):
        """Test adding multiple sources at once."""
        assembler = ContextAssembler()
        sources = [
            ContentSource(source_id="a", content="A"),
            ContentSource(source_id="b", content="B"),
        ]

        assembler.add_sources(sources)

        self.assertEqual(len(assembler.sources), 2)

    def test_clear_sources(self):
        """Test clearing sources."""
        assembler = ContextAssembler()
        assembler.add_source(ContentSource(source_id="a", content="A"))
        assembler.clear_sources()

        self.assertEqual(len(assembler.sources), 0)

    def test_assemble_empty(self):
        """Test assembling with no sources."""
        assembler = ContextAssembler()

        result = assembler.assemble(max_tokens=1000)

        self.assertEqual(result.content, "")
        self.assertEqual(result.total_tokens, 0)

    def test_assemble_priority_first(self):
        """Test priority-first assembly."""
        assembler = ContextAssembler()
        assembler.add_source(ContentSource(source_id="low", content="Low", priority=10))
        assembler.add_source(ContentSource(source_id="high", content="High", priority=1))
        assembler.add_source(ContentSource(source_id="med", content="Medium", priority=5))

        result = assembler.assemble(
            strategy=AssemblyStrategy.PRIORITY_FIRST,
            max_tokens=1000,
        )

        self.assertEqual(result.strategy, AssemblyStrategy.PRIORITY_FIRST)
        # High priority should be first
        self.assertEqual(result.included_sources[0], "high")

    def test_assemble_priority_budget_limit(self):
        """Test priority assembly respects budget."""
        assembler = ContextAssembler()
        # Add sources that exceed budget
        assembler.add_source(ContentSource(
            source_id="a", content="x" * 400, priority=1, token_estimate=100
        ))
        assembler.add_source(ContentSource(
            source_id="b", content="y" * 400, priority=2, token_estimate=100
        ))
        assembler.add_source(ContentSource(
            source_id="c", content="z" * 400, priority=3, token_estimate=100
        ))

        result = assembler.assemble(
            strategy=AssemblyStrategy.PRIORITY_FIRST,
            max_tokens=150,  # Only fits first source
        )

        self.assertIn("a", result.included_sources)
        self.assertIn("b", result.excluded_sources)

    def test_assemble_token_balanced(self):
        """Test token-balanced assembly."""
        assembler = ContextAssembler()
        assembler.add_source(ContentSource(
            source_id="a", content="x" * 800, token_estimate=200
        ))
        assembler.add_source(ContentSource(
            source_id="b", content="y" * 800, token_estimate=200
        ))

        result = assembler.assemble(
            strategy=AssemblyStrategy.TOKEN_BALANCED,
            max_tokens=200,  # 100 each
        )

        self.assertEqual(result.strategy, AssemblyStrategy.TOKEN_BALANCED)
        # Both sources should be included (truncated)
        self.assertIn("a", result.included_sources)
        self.assertIn("b", result.included_sources)

    def test_assemble_progressive(self):
        """Test progressive assembly."""
        assembler = ContextAssembler()
        assembler.add_source(ContentSource(
            source_id="a", content="x" * 800, token_estimate=200, priority=1
        ))
        assembler.add_source(ContentSource(
            source_id="b", content="y" * 800, token_estimate=200, priority=2
        ))

        result = assembler.assemble(
            strategy=AssemblyStrategy.PROGRESSIVE,
            max_tokens=1000,
            initial_depth=0.5,
        )

        self.assertEqual(result.strategy, AssemblyStrategy.PROGRESSIVE)
        self.assertTrue(result.expansion_available)

    def test_assemble_hybrid(self):
        """Test hybrid assembly."""
        assembler = ContextAssembler()
        # Critical (priority <= 2)
        assembler.add_source(ContentSource(source_id="crit", content="x" * 400, priority=1))
        # Non-critical
        assembler.add_source(ContentSource(source_id="other", content="y" * 400, priority=5))

        result = assembler.assemble(
            strategy=AssemblyStrategy.HYBRID,
            max_tokens=500,
            critical_ratio=0.6,
        )

        self.assertEqual(result.strategy, AssemblyStrategy.HYBRID)
        self.assertIn("crit", result.included_sources)

    def test_assemble_greedy(self):
        """Test greedy assembly."""
        assembler = ContextAssembler()
        # Smaller sources should be packed first
        assembler.add_source(ContentSource(source_id="large", content="x" * 800, priority=1))
        assembler.add_source(ContentSource(source_id="small", content="y" * 200, priority=2))

        result = assembler.assemble(
            strategy=AssemblyStrategy.GREEDY,
            max_tokens=300,
        )

        self.assertEqual(result.strategy, AssemblyStrategy.GREEDY)
        # Small should definitely fit
        self.assertIn("small", result.included_sources)

    def test_assembled_context_to_dict(self):
        """Test result serialization."""
        assembler = ContextAssembler()
        assembler.add_source(ContentSource(source_id="a", content="A"))

        result = assembler.assemble(max_tokens=1000)
        data = result.to_dict()

        self.assertIn("content", data)
        self.assertIn("included_sources", data)
        self.assertIn("strategy", data)
        self.assertIn("total_tokens", data)


class TestAssemblyConvenience(unittest.TestCase):
    """Test assembly convenience functions."""

    def test_assemble_for_finding(self):
        """Test document assembly for finding."""
        docs = [create_test_doc()]

        result = assemble_for_finding(
            documents=docs,
            max_tokens=2000,
            strategy=AssemblyStrategy.PRIORITY_FIRST,
        )

        self.assertIsInstance(result, AssembledContext)
        self.assertGreater(len(result.content), 0)

    def test_quick_assemble(self):
        """Test quick assembly function."""
        contents = {
            "detection": "Detection content",
            "mitigation": "Mitigation content",
        }
        priorities = {
            "detection": 1,
            "mitigation": 2,
        }

        result = quick_assemble(contents, priorities, max_tokens=1000)

        self.assertIn("Detection content", result)
        self.assertIn("Mitigation content", result)


# =============================================================================
# Integration Tests
# =============================================================================

class TestContextIntegration(unittest.TestCase):
    """Integration tests for context system."""

    def test_builder_with_cache_manager(self):
        """Test builder integration with cache manager."""
        manager = PromptCacheManager()

        # Set up cached context
        manager.set_system_context("VulnDocs Navigation Guide")
        manager.set_category_context("reentrancy", "Reentrancy Overview")

        # Build context set
        ctx_set = manager.build_context_set(
            categories=["reentrancy"],
            dynamic_content="Finding: state_write_after_external_call",
        )

        # Verify structure
        blocks = ctx_set.to_anthropic_blocks()
        self.assertEqual(len(blocks), 3)

        # First two should be cacheable
        self.assertIn("cache_control", blocks[0])
        self.assertIn("cache_control", blocks[1])
        self.assertNotIn("cache_control", blocks[2])

    def test_full_workflow(self):
        """Test complete context building workflow."""
        # 1. Create assembler with sources
        assembler = ContextAssembler()
        assembler.add_source(ContentSource(
            source_id="detection",
            content="## Detection\nLook for state updates after external calls",
            priority=1,
        ))
        assembler.add_source(ContentSource(
            source_id="mitigation",
            content="## Mitigation\nUse CEI pattern",
            priority=2,
        ))

        # 2. Assemble context
        assembled = assembler.assemble(
            strategy=AssemblyStrategy.PRIORITY_FIRST,
            max_tokens=1000,
        )

        # 3. Create cache manager
        manager = PromptCacheManager()
        manager.set_system_context(assembled.content)

        # 4. Build final context set
        ctx_set = manager.build_context_set(
            dynamic_content="Specific finding details",
        )

        # Verify
        self.assertGreater(ctx_set.get_total_tokens(), 0)
        combined = ctx_set.get_combined_content()
        self.assertIn("Detection", combined)
        self.assertIn("Mitigation", combined)


if __name__ == "__main__":
    unittest.main()
