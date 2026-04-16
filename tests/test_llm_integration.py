"""Tests for Phase 12: LLM Integration.

Tests cover:
- P12-T1: Annotation Schema
- P12-T2: Step-Back Prompting
- P12-T3: RAG with Pattern Library
- P12-T4: Annotation Caching
"""

import unittest
import tempfile
import os

from alphaswarm_sol.kg.schema import Node
from alphaswarm_sol.llm.annotations import (
    AnnotationType,
    AnnotationSource,
    LLMAnnotation,
    AnnotationSet,
    create_annotation,
    merge_annotations,
)
from alphaswarm_sol.llm.prompts import (
    PromptStyle,
    StepBackPrompt,
    AnalysisPrompt,
    PromptBuilder,
    generate_analysis_prompt,
    generate_step_back_prompt,
)
from alphaswarm_sol.llm.cache import (
    CacheEntry,
    AnnotationCache,
    get_cache,
    clear_cache,
)
from alphaswarm_sol.llm.rag import (
    RAGResult,
    PatternEntry,
    PatternRAG,
    retrieve_similar_patterns,
    build_rag_context,
)


class TestAnnotationSchema(unittest.TestCase):
    """Tests for LLM annotation schema."""

    def test_annotation_type_values(self):
        """Test annotation type enum values."""
        self.assertEqual(AnnotationType.RISK_ASSESSMENT.value, "risk_assessment")
        self.assertEqual(AnnotationType.INTENT_ANALYSIS.value, "intent_analysis")

    def test_annotation_source_values(self):
        """Test annotation source enum values."""
        self.assertEqual(AnnotationSource.LLM_GPT4.value, "llm_gpt4")
        self.assertEqual(AnnotationSource.LLM_CLAUDE.value, "llm_claude")

    def test_annotation_creation(self):
        """Test creating an annotation."""
        ann = LLMAnnotation(
            node_id="fn1",
            annotation_type=AnnotationType.RISK_ASSESSMENT,
            risk_tags=["reentrancy", "high_risk"],
            confidence=0.95,
            description="Potential reentrancy vulnerability detected",
            developer_intent="Withdraw user funds",
            business_context="DeFi lending protocol",
            source=AnnotationSource.LLM_CLAUDE,
            model="claude-3-opus",
        )

        self.assertEqual(ann.node_id, "fn1")
        self.assertEqual(ann.confidence, 0.95)
        self.assertIn("reentrancy", ann.risk_tags)
        self.assertIsNotNone(ann.timestamp)

    def test_annotation_to_dict(self):
        """Test annotation serialization."""
        ann = LLMAnnotation(
            node_id="fn1",
            annotation_type=AnnotationType.VULNERABILITY_EXPLANATION,
            description="Test description",
            confidence=0.8,
        )

        data = ann.to_dict()
        self.assertEqual(data["node_id"], "fn1")
        self.assertEqual(data["annotation_type"], "vulnerability_explanation")
        self.assertEqual(data["confidence"], 0.8)

    def test_annotation_from_dict(self):
        """Test annotation deserialization."""
        data = {
            "node_id": "fn2",
            "annotation_type": "intent_analysis",
            "risk_tags": ["access_control"],
            "confidence": 0.75,
            "description": "Admin function",
        }

        ann = LLMAnnotation.from_dict(data)
        self.assertEqual(ann.node_id, "fn2")
        self.assertEqual(ann.annotation_type, AnnotationType.INTENT_ANALYSIS)
        self.assertIn("access_control", ann.risk_tags)

    def test_annotation_hash(self):
        """Test annotation hash for caching."""
        ann = LLMAnnotation(
            node_id="fn1",
            annotation_type=AnnotationType.RISK_ASSESSMENT,
            description="Test",
        )

        hash1 = ann.get_hash()
        self.assertEqual(len(hash1), 16)

        # Same content should give same hash
        ann2 = LLMAnnotation(
            node_id="fn1",
            annotation_type=AnnotationType.RISK_ASSESSMENT,
            description="Test",
        )
        self.assertEqual(ann.get_hash(), ann2.get_hash())

    def test_create_annotation_helper(self):
        """Test create_annotation helper function."""
        ann = create_annotation(
            node_id="fn1",
            ann_type=AnnotationType.REMEDIATION_SUGGESTION,
            description="Add reentrancy guard",
            confidence=0.9,
            risk_tags=["reentrancy"],
            model="test-model",
        )

        self.assertEqual(ann.node_id, "fn1")
        self.assertEqual(ann.annotation_type, AnnotationType.REMEDIATION_SUGGESTION)
        self.assertEqual(ann.model, "test-model")

    def test_merge_annotations(self):
        """Test merging multiple annotations."""
        ann1 = LLMAnnotation(
            node_id="fn1",
            annotation_type=AnnotationType.RISK_ASSESSMENT,
            risk_tags=["reentrancy"],
            confidence=0.9,
            description="High risk reentrancy",
        )
        ann2 = LLMAnnotation(
            node_id="fn1",
            annotation_type=AnnotationType.RISK_ASSESSMENT,
            risk_tags=["access_control"],
            confidence=0.7,
            description="Missing access control",
        )

        merged = merge_annotations([ann1, ann2])

        self.assertEqual(merged.confidence, 0.9)  # Takes highest
        self.assertIn("reentrancy", merged.risk_tags)
        self.assertIn("access_control", merged.risk_tags)
        self.assertEqual(merged.metadata["merged_from"], 2)

    def test_annotation_set(self):
        """Test AnnotationSet class."""
        ann_set = AnnotationSet(node_id="fn1")

        ann_set.add(create_annotation(
            node_id="fn1",
            ann_type=AnnotationType.RISK_ASSESSMENT,
            description="Risk 1",
            confidence=0.9,
        ))
        ann_set.add(create_annotation(
            node_id="fn1",
            ann_type=AnnotationType.INTENT_ANALYSIS,
            description="Intent 1",
            confidence=0.7,
        ))

        self.assertEqual(len(ann_set.annotations), 2)
        self.assertEqual(len(ann_set.get_by_type(AnnotationType.RISK_ASSESSMENT)), 1)
        self.assertEqual(len(ann_set.get_high_confidence(0.8)), 1)


class TestStepBackPrompting(unittest.TestCase):
    """Tests for step-back prompting."""

    def test_step_back_prompt_creation(self):
        """Test creating step-back prompt."""
        prompt = StepBackPrompt(
            context="What are reentrancy vulnerabilities?",
            specific="Is this function vulnerable?",
            background="Smart contract security expert",
        )

        self.assertEqual(prompt.context, "What are reentrancy vulnerabilities?")
        self.assertEqual(prompt.specific, "Is this function vulnerable?")

    def test_step_back_to_messages(self):
        """Test converting to message format."""
        prompt = StepBackPrompt(
            context="General question",
            specific="Specific question",
            background="Background info",
            examples=[
                {"question": "Q1", "answer": "A1"},
            ],
        )

        messages = prompt.to_messages()

        # Should have system, example Q, example A, context, specific
        self.assertGreater(len(messages), 3)
        self.assertEqual(messages[0]["role"], "system")

    def test_step_back_to_single_prompt(self):
        """Test converting to single prompt string."""
        prompt = StepBackPrompt(
            context="General question",
            specific="Specific question",
            background="Background info",
        )

        text = prompt.to_single_prompt()
        self.assertIn("step back", text.lower())
        self.assertIn("General question", text)
        self.assertIn("Specific question", text)

    def test_generate_step_back_prompt(self):
        """Test generate_step_back_prompt helper."""
        prompt = generate_step_back_prompt(
            function_summary="withdraw() function transfers ETH",
            vulnerability_type="reentrancy",
        )

        self.assertIn("reentrancy", prompt.context.lower())
        self.assertIn("withdraw", prompt.specific)


class TestAnalysisPrompt(unittest.TestCase):
    """Tests for analysis prompts."""

    def test_analysis_prompt_creation(self):
        """Test creating analysis prompt."""
        prompt = AnalysisPrompt(
            code="function withdraw() public { msg.sender.transfer(balance); }",
            function_name="withdraw",
            properties={"has_external_calls": True},
            context="DeFi protocol",
        )

        self.assertEqual(prompt.function_name, "withdraw")
        self.assertIn("has_external_calls", prompt.properties)

    def test_analysis_prompt_to_prompt(self):
        """Test generating prompt string."""
        prompt = AnalysisPrompt(
            code="function test() public {}",
            function_name="test",
            properties={"visibility": "public"},
            query="Is this function secure?",
        )

        text = prompt.to_prompt()
        self.assertIn("function test()", text)
        self.assertIn("visibility", text)
        self.assertIn("Is this function secure?", text)

    def test_prompt_builder(self):
        """Test PromptBuilder fluent interface."""
        builder = PromptBuilder()

        prompt = (
            builder
            .system("You are a security expert")
            .add_context("Analyzing DeFi protocol")
            .code("function foo() {}", "foo")
            .properties({"has_access_gate": True})
            .query("Find vulnerabilities")
            .style(PromptStyle.STEP_BACK)
            .build()
        )

        self.assertIn("security expert", prompt)
        self.assertIn("function foo()", prompt)
        self.assertIn("has_access_gate", prompt)
        self.assertIn("Step 1", prompt)  # Step-back style

    def test_prompt_builder_messages(self):
        """Test PromptBuilder message format."""
        builder = PromptBuilder()
        builder.system("System message")
        builder.query("Test query")

        messages = builder.build_messages()
        self.assertEqual(messages[0]["role"], "system")
        self.assertGreater(len(messages), 0)

    def test_generate_analysis_prompt(self):
        """Test generate_analysis_prompt helper."""
        prompt = generate_analysis_prompt(
            code="function x() {}",
            function_name="x",
            properties={"visibility": "public"},
            context="Test context",
        )

        self.assertIn("function x()", prompt)
        self.assertIn("visibility", prompt)


class TestAnnotationCache(unittest.TestCase):
    """Tests for annotation caching."""

    def setUp(self):
        """Clear global cache before each test."""
        clear_cache()

    def test_cache_creation(self):
        """Test creating cache."""
        cache = AnnotationCache(max_size=100, default_ttl=3600)
        self.assertEqual(cache.max_size, 100)
        self.assertEqual(len(cache._cache), 0)

    def test_cache_put_get(self):
        """Test basic put/get operations."""
        cache = AnnotationCache()

        ann = create_annotation(
            node_id="fn1",
            ann_type=AnnotationType.RISK_ASSESSMENT,
            description="Test",
            confidence=0.9,
        )

        cache.put("fn1", "analyze risks", ann)
        result = cache.get("fn1", "analyze risks")

        self.assertIsNotNone(result)
        self.assertEqual(result.description, "Test")

    def test_cache_miss(self):
        """Test cache miss."""
        cache = AnnotationCache()
        result = cache.get("nonexistent", "query")
        self.assertIsNone(result)

    def test_cache_expiration(self):
        """Test cache entry expiration."""
        cache = AnnotationCache(default_ttl=0.001)  # 1ms TTL

        ann = create_annotation(
            node_id="fn1",
            ann_type=AnnotationType.RISK_ASSESSMENT,
            description="Test",
        )
        cache.put("fn1", "query", ann)

        import time
        time.sleep(0.01)  # Wait for expiration

        result = cache.get("fn1", "query")
        self.assertIsNone(result)

    def test_cache_invalidation(self):
        """Test cache invalidation."""
        cache = AnnotationCache()

        ann = create_annotation(
            node_id="fn1",
            ann_type=AnnotationType.RISK_ASSESSMENT,
            description="Test",
        )
        cache.put("fn1", "query", ann)

        # Invalidate
        removed = cache.invalidate("fn1", "query")
        self.assertTrue(removed)

        result = cache.get("fn1", "query")
        self.assertIsNone(result)

    def test_cache_stats(self):
        """Test cache statistics."""
        cache = AnnotationCache()

        ann = create_annotation(
            node_id="fn1",
            ann_type=AnnotationType.RISK_ASSESSMENT,
            description="Test",
        )
        cache.put("fn1", "query", ann)
        cache.get("fn1", "query")  # Hit
        cache.get("fn1", "other")  # Miss

        stats = cache.get_stats()
        self.assertEqual(stats["hits"], 1)
        self.assertEqual(stats["misses"], 1)
        self.assertEqual(stats["size"], 1)

    def test_cache_lru_eviction(self):
        """Test LRU eviction when at capacity."""
        cache = AnnotationCache(max_size=2)

        for i in range(3):
            ann = create_annotation(
                node_id=f"fn{i}",
                ann_type=AnnotationType.RISK_ASSESSMENT,
                description=f"Test {i}",
            )
            cache.put(f"fn{i}", "query", ann)

        # Should have evicted the least recently used
        self.assertEqual(len(cache._cache), 2)

    def test_cache_persistence(self):
        """Test cache persistence to disk."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_path = os.path.join(tmpdir, "cache.json")

            # Create and populate cache
            cache1 = AnnotationCache(persist_path=cache_path)
            ann = create_annotation(
                node_id="fn1",
                ann_type=AnnotationType.RISK_ASSESSMENT,
                description="Test",
            )
            cache1.put("fn1", "query", ann)

            # Create new cache from same file
            cache2 = AnnotationCache(persist_path=cache_path)
            result = cache2.get("fn1", "query")

            self.assertIsNotNone(result)
            self.assertEqual(result.description, "Test")

    def test_global_cache(self):
        """Test global cache functions."""
        cache = get_cache()
        self.assertIsNotNone(cache)

        clear_cache()
        cache2 = get_cache()
        # After clear, should get a new cache
        self.assertIsNotNone(cache2)


class TestCacheEntry(unittest.TestCase):
    """Tests for CacheEntry."""

    def test_cache_entry_creation(self):
        """Test creating cache entry."""
        ann = create_annotation(
            node_id="fn1",
            ann_type=AnnotationType.RISK_ASSESSMENT,
            description="Test",
        )

        entry = CacheEntry(key="test_key", annotation=ann)
        self.assertEqual(entry.key, "test_key")
        self.assertEqual(entry.hit_count, 0)

    def test_cache_entry_not_expired(self):
        """Test non-expired entry."""
        ann = create_annotation(
            node_id="fn1",
            ann_type=AnnotationType.RISK_ASSESSMENT,
            description="Test",
        )
        entry = CacheEntry(key="test", annotation=ann)
        # No expires_at = never expires
        self.assertFalse(entry.is_expired())

    def test_cache_entry_record_hit(self):
        """Test recording cache hits."""
        ann = create_annotation(
            node_id="fn1",
            ann_type=AnnotationType.RISK_ASSESSMENT,
            description="Test",
        )
        entry = CacheEntry(key="test", annotation=ann)

        entry.record_hit()
        entry.record_hit()

        self.assertEqual(entry.hit_count, 2)


class TestPatternRAG(unittest.TestCase):
    """Tests for RAG with pattern library."""

    def test_rag_result_creation(self):
        """Test creating RAG result."""
        result = RAGResult(
            pattern_id="reentrancy-001",
            pattern_name="Classic Reentrancy",
            similarity_score=0.95,
            pattern_description="External call before state update",
            match_reason="Exact signature match",
            remediation="Use ReentrancyGuard",
        )

        self.assertEqual(result.pattern_id, "reentrancy-001")
        self.assertEqual(result.similarity_score, 0.95)

    def test_rag_result_to_context(self):
        """Test converting RAG result to context string."""
        result = RAGResult(
            pattern_id="test-001",
            pattern_name="Test Pattern",
            similarity_score=0.8,
            pattern_description="Test description",
            remediation="Test fix",
        )

        context = result.to_context_string()
        self.assertIn("Test Pattern", context)
        self.assertIn("Test description", context)

    def test_pattern_entry_from_yaml(self):
        """Test creating pattern from YAML data."""
        data = {
            "id": "test-001",
            "name": "Test Pattern",
            "description": "Test description",
            "severity": "high",
            "behavioral_signature": "R:bal→X:out→W:bal",
            "required_operations": ["TRANSFERS_VALUE_OUT"],
            "remediation": "Apply fix",
        }

        pattern = PatternEntry.from_yaml(data)
        self.assertEqual(pattern.id, "test-001")
        self.assertEqual(pattern.severity, "high")
        self.assertEqual(pattern.behavioral_signature, "R:bal→X:out→W:bal")

    def test_pattern_rag_add_pattern(self):
        """Test adding patterns to RAG."""
        rag = PatternRAG()

        pattern = PatternEntry(
            id="test-001",
            name="Test Pattern",
            behavioral_signature="R:bal→X:out",
            required_operations=["TRANSFERS_VALUE_OUT"],
        )
        rag.add_pattern(pattern)

        self.assertEqual(len(rag.patterns), 1)
        self.assertIn("R:bal→X:out", rag._signature_index)

    def test_pattern_rag_retrieve(self):
        """Test retrieving patterns for a function."""
        rag = PatternRAG()

        # Add a pattern
        pattern = PatternEntry(
            id="reentrancy-001",
            name="Reentrancy",
            description="Classic reentrancy",
            behavioral_signature="R:bal→X:out→W:bal",
            required_operations=["TRANSFERS_VALUE_OUT", "WRITES_USER_BALANCE"],
            remediation="Use CEI pattern",
        )
        rag.add_pattern(pattern)

        # Create matching function
        fn = Node(
            id="fn1",
            type="Function",
            label="withdraw",
            properties={
                "behavioral_signature": "R:bal→X:out→W:bal",
                "semantic_ops": ["TRANSFERS_VALUE_OUT", "WRITES_USER_BALANCE"],
            },
        )

        results = rag.retrieve(fn, top_k=5)

        self.assertGreater(len(results), 0)
        self.assertEqual(results[0].pattern_id, "reentrancy-001")
        self.assertEqual(results[0].similarity_score, 1.0)

    def test_pattern_rag_retrieve_by_query(self):
        """Test retrieving patterns by text query."""
        rag = PatternRAG()

        pattern = PatternEntry(
            id="access-001",
            name="Missing Access Control",
            description="Public function modifies privileged state",
            required_operations=["MODIFIES_OWNER"],
        )
        rag.add_pattern(pattern)

        results = rag.retrieve_by_query("access control owner")

        self.assertGreater(len(results), 0)
        self.assertEqual(results[0].pattern_id, "access-001")

    def test_build_rag_context(self):
        """Test building RAG context for LLM."""
        fn = Node(id="fn1", type="Function", label="test", properties={})
        results = [
            RAGResult(
                pattern_id="test-001",
                pattern_name="Test Pattern",
                similarity_score=0.9,
                match_reason="Test match",
                remediation="Test fix",
            )
        ]

        context = build_rag_context(fn, results)

        self.assertIn("Test Pattern", context)
        self.assertIn("90%", context)
        self.assertIn("Test fix", context)

    def test_build_rag_context_empty(self):
        """Test building RAG context with no results."""
        fn = Node(id="fn1", type="Function", label="test", properties={})
        context = build_rag_context(fn, [])
        self.assertEqual(context, "")


class TestPatternRAGWithFiles(unittest.TestCase):
    """Tests for PatternRAG with actual pattern files."""

    def test_load_patterns_from_directory(self):
        """Test loading patterns from directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a test pattern file
            pattern_content = """
id: test-pattern-001
name: Test Pattern
description: A test pattern
severity: high
behavioral_signature: R:bal→X:out
required_operations:
  - TRANSFERS_VALUE_OUT
remediation: Apply the fix
"""
            pattern_file = os.path.join(tmpdir, "test.yaml")
            with open(pattern_file, "w") as f:
                f.write(pattern_content)

            rag = PatternRAG(patterns_dir=tmpdir)

            self.assertEqual(len(rag.patterns), 1)
            self.assertEqual(rag.patterns[0].id, "test-pattern-001")


if __name__ == "__main__":
    unittest.main()
