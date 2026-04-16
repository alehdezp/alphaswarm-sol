"""Tests for VulnDocs storage and retrieval system.

Task 18.14-18.17: Tests for KnowledgeStore, IndexBuilder, and KnowledgeRetriever.
"""

import json
import shutil
import tempfile
import unittest
from pathlib import Path
from typing import List

from alphaswarm_sol.vulndocs.knowledge_doc import (
    DetectionSection,
    DocMetadata,
    ExamplesSection,
    ExploitationSection,
    MitigationSection,
    PatternLinkage,
    PatternLinkageType,
    RealExploitRef,
    Severity,
    VulnKnowledgeDoc,
)
from alphaswarm_sol.vulndocs.storage.knowledge_store import (
    DocumentExistsError,
    DocumentNotFoundError,
    KnowledgeStore,
    StorageConfig,
    StorageError,
)
from alphaswarm_sol.vulndocs.storage.index_builder import (
    CategorySummary,
    IndexBuilder,
    IndexEntry,
    KnowledgeIndex,
)
from alphaswarm_sol.vulndocs.storage.retrieval import (
    KnowledgeRetriever,
    RetrievalConfig,
    RetrievalDepth,
    RetrievalQuery,
    RetrievalResult,
)


def create_test_document(
    doc_id: str = "reentrancy/classic/test-doc",
    name: str = "Test Vulnerability",
    category: str = "reentrancy",
    subcategory: str = "classic",
    severity: Severity = Severity.HIGH,
    keywords: List[str] = None,
    pattern_ids: List[str] = None,
) -> VulnKnowledgeDoc:
    """Create a test document with default values."""
    return VulnKnowledgeDoc(
        id=doc_id,
        name=name,
        category=category,
        subcategory=subcategory,
        severity=severity,
        one_liner="Test vulnerability description",
        tldr="This is a test vulnerability for testing purposes.",
        detection=DetectionSection(
            graph_signals=["state_write_after_external_call", "no_reentrancy_guard"],
            vulnerable_sequence="R:bal -> X:out -> W:bal",
            safe_sequence="R:bal -> W:bal -> X:out",
            indicators=["External call before state update"],
            checklist=["Check call ordering", "Verify guard presence"],
        ),
        exploitation=ExploitationSection(
            attack_vector="Callback exploitation",
            prerequisites=["External call to attacker contract"],
            attack_steps=["Deploy attacker", "Call withdraw", "Re-enter"],
            potential_impact="Complete fund drain",
            monetary_risk="critical",
        ),
        mitigation=MitigationSection(
            primary_fix="Use CEI pattern",
            alternative_fixes=["Use reentrancy guard"],
            safe_pattern="CEI",
            how_to_verify=["Test with attacker contract"],
        ),
        examples=ExamplesSection(
            vulnerable_code="function withdraw() { msg.sender.call{value: bal}(''); }",
            vulnerable_code_explanation="External call before state update",
            fixed_code="function withdraw() { uint b = bal; bal = 0; msg.sender.call{value: b}(''); }",
            fixed_code_explanation="State updated before external call",
            real_exploits=[
                RealExploitRef(
                    name="The DAO Hack",
                    date="2016-06-17",
                    loss="$60M",
                    protocol="The DAO",
                    brief="Classic reentrancy exploit",
                )
            ],
        ),
        pattern_linkage=PatternLinkage(
            linkage_type=PatternLinkageType.EXACT_MATCH,
            pattern_ids=pattern_ids or ["reentrancy-001"],
            coverage_pct=0.95,
        ),
        metadata=DocMetadata(
            sources=["https://example.com/vuln"],
            source_authority=0.9,
            keywords=keywords or ["reentrancy", "external-call", "state-update"],
            completeness_score=0.85,
            confidence_score=0.9,
        ),
    )


class TestKnowledgeStore(unittest.TestCase):
    """Tests for KnowledgeStore."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.config = StorageConfig(
            base_path=self.temp_dir,
            auto_create_dirs=True,
            pretty_json=True,
        )
        self.store = KnowledgeStore(self.config)

    def tearDown(self):
        """Clean up after tests."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_save_and_load_document(self):
        """Test basic save and load."""
        doc = create_test_document()

        path = self.store.save(doc)
        self.assertTrue(Path(path).exists())

        loaded = self.store.load(doc.id)
        self.assertEqual(loaded.id, doc.id)
        self.assertEqual(loaded.name, doc.name)
        self.assertEqual(loaded.severity, doc.severity)

    def test_exists(self):
        """Test document existence check."""
        doc = create_test_document()

        self.assertFalse(self.store.exists(doc.id))
        self.store.save(doc)
        self.assertTrue(self.store.exists(doc.id))

    def test_delete(self):
        """Test document deletion."""
        doc = create_test_document()
        self.store.save(doc)

        self.assertTrue(self.store.exists(doc.id))
        result = self.store.delete(doc.id)
        self.assertTrue(result)
        self.assertFalse(self.store.exists(doc.id))

    def test_delete_nonexistent(self):
        """Test deleting non-existent document."""
        result = self.store.delete("nonexistent/doc/id")
        self.assertFalse(result)

    def test_load_nonexistent(self):
        """Test loading non-existent document."""
        with self.assertRaises(DocumentNotFoundError):
            self.store.load("nonexistent/doc/id")

    def test_save_no_overwrite(self):
        """Test save with overwrite=False."""
        doc = create_test_document()
        self.store.save(doc)

        with self.assertRaises(DocumentExistsError):
            self.store.save(doc, overwrite=False)

    def test_save_with_overwrite(self):
        """Test save with overwrite=True."""
        doc = create_test_document()
        self.store.save(doc)

        doc.name = "Updated Name"
        self.store.save(doc, overwrite=True)

        loaded = self.store.load(doc.id)
        self.assertEqual(loaded.name, "Updated Name")

    def test_list_documents(self):
        """Test listing documents."""
        doc1 = create_test_document("reentrancy/classic/doc1")
        doc2 = create_test_document("reentrancy/classic/doc2")
        doc3 = create_test_document("access-control/missing-modifier/doc1")

        self.store.save(doc1)
        self.store.save(doc2)
        self.store.save(doc3)

        # List all
        all_docs = self.store.list_documents()
        self.assertEqual(len(all_docs), 3)

        # List by category
        reentrancy_docs = self.store.list_documents(category="reentrancy")
        self.assertEqual(len(reentrancy_docs), 2)

        # List by subcategory
        classic_docs = self.store.list_documents(
            category="reentrancy", subcategory="classic"
        )
        self.assertEqual(len(classic_docs), 2)

    def test_list_categories(self):
        """Test listing categories."""
        doc1 = create_test_document("reentrancy/classic/doc1")
        doc2 = create_test_document("access-control/missing-modifier/doc1")

        self.store.save(doc1)
        self.store.save(doc2)

        categories = self.store.list_categories()
        self.assertIn("reentrancy", categories)
        self.assertIn("access-control", categories)

    def test_list_subcategories(self):
        """Test listing subcategories."""
        doc1 = create_test_document("reentrancy/classic/doc1")
        doc2 = create_test_document("reentrancy/cross-function/doc1")

        self.store.save(doc1)
        self.store.save(doc2)

        subcategories = self.store.list_subcategories("reentrancy")
        self.assertIn("classic", subcategories)
        self.assertIn("cross-function", subcategories)

    def test_batch_save_and_load(self):
        """Test batch operations."""
        docs = [
            create_test_document(f"reentrancy/classic/doc{i}")
            for i in range(5)
        ]

        paths = self.store.save_batch(docs)
        self.assertEqual(len(paths), 5)

        doc_ids = [d.id for d in docs]
        loaded = self.store.load_batch(doc_ids)
        self.assertEqual(len(loaded), 5)

    def test_load_category(self):
        """Test loading all documents in a category."""
        doc1 = create_test_document("reentrancy/classic/doc1")
        doc2 = create_test_document("reentrancy/cross-function/doc1")
        doc3 = create_test_document("access-control/missing-modifier/doc1")

        self.store.save(doc1)
        self.store.save(doc2)
        self.store.save(doc3)

        reentrancy_docs = self.store.load_category("reentrancy")
        self.assertEqual(len(reentrancy_docs), 2)

    def test_iterate_documents(self):
        """Test document iteration."""
        for i in range(3):
            doc = create_test_document(f"reentrancy/classic/doc{i}")
            self.store.save(doc)

        count = 0
        for doc in self.store.iterate_documents():
            count += 1
            self.assertIsInstance(doc, VulnKnowledgeDoc)

        self.assertEqual(count, 3)

    def test_get_stats(self):
        """Test storage statistics."""
        doc1 = create_test_document("reentrancy/classic/doc1")
        doc2 = create_test_document("access-control/missing-modifier/doc1")

        self.store.save(doc1)
        self.store.save(doc2)

        stats = self.store.get_stats()
        self.assertEqual(stats.total_documents, 2)
        self.assertEqual(stats.total_categories, 2)
        self.assertIn("reentrancy", stats.documents_by_category)

    def test_clear(self):
        """Test clearing all documents."""
        for i in range(3):
            doc = create_test_document(f"reentrancy/classic/doc{i}")
            self.store.save(doc)

        count = self.store.clear()
        self.assertEqual(count, 3)
        self.assertEqual(len(self.store.list_documents()), 0)

    def test_search_by_keyword(self):
        """Test keyword search."""
        doc1 = create_test_document(
            "reentrancy/classic/doc1", keywords=["reentrancy", "callback"]
        )
        doc2 = create_test_document(
            "access-control/missing-modifier/doc1", keywords=["access", "modifier"]
        )

        self.store.save(doc1)
        self.store.save(doc2)

        results = self.store.search_by_keyword(["reentrancy"])
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].id, doc1.id)

    def test_search_by_severity(self):
        """Test severity search."""
        doc1 = create_test_document(
            "reentrancy/classic/doc1", severity=Severity.CRITICAL
        )
        doc2 = create_test_document(
            "reentrancy/classic/doc2", severity=Severity.LOW
        )

        self.store.save(doc1)
        self.store.save(doc2)

        results = self.store.search_by_severity("critical")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].id, doc1.id)

    def test_has_changed(self):
        """Test change detection."""
        doc = create_test_document()
        self.store.save(doc)

        # No change
        self.assertFalse(self.store.has_changed(doc))

        # Change the doc
        doc.name = "Changed Name"
        doc.metadata.content_hash = doc._compute_hash()
        self.assertTrue(self.store.has_changed(doc))

    def test_save_if_changed(self):
        """Test save-if-changed."""
        doc = create_test_document()
        self.store.save(doc)

        # No change - should not save
        saved = self.store.save_if_changed(doc)
        self.assertFalse(saved)

        # Change - should save
        doc.name = "Changed Name"
        doc.metadata.content_hash = doc._compute_hash()
        saved = self.store.save_if_changed(doc)
        self.assertTrue(saved)

    def test_export_import(self):
        """Test export and import."""
        doc1 = create_test_document("reentrancy/classic/doc1")
        doc2 = create_test_document("access-control/missing-modifier/doc1")

        self.store.save(doc1)
        self.store.save(doc2)

        # Export
        export_data = self.store.export_to_dict()
        self.assertEqual(export_data["stats"]["total_documents"], 2)

        # Clear and import
        self.store.clear()
        count = self.store.import_from_dict(export_data)
        self.assertEqual(count, 2)


class TestIndexBuilder(unittest.TestCase):
    """Tests for IndexBuilder."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.config = StorageConfig(base_path=self.temp_dir)
        self.store = KnowledgeStore(self.config)
        self.builder = IndexBuilder(self.store)

    def tearDown(self):
        """Clean up after tests."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_build_empty_index(self):
        """Test building index with no documents."""
        index = self.builder.build()
        self.assertEqual(index.total_documents, 0)
        self.assertEqual(len(index.entries), 0)

    def test_build_index(self):
        """Test building index with documents."""
        doc1 = create_test_document(
            "reentrancy/classic/doc1",
            keywords=["reentrancy"],
            pattern_ids=["reentrancy-001"],
        )
        doc2 = create_test_document(
            "access-control/missing-modifier/doc1",
            category="access-control",
            subcategory="missing-modifier",
            keywords=["access"],
            pattern_ids=["access-001"],
        )

        self.store.save(doc1)
        self.store.save(doc2)

        index = self.builder.build()

        self.assertEqual(index.total_documents, 2)
        self.assertEqual(len(index.entries), 2)
        self.assertEqual(len(index.categories), 2)

    def test_index_entry_creation(self):
        """Test creating index entry from document."""
        doc = create_test_document()
        entry = IndexEntry.from_document(doc)

        self.assertEqual(entry.doc_id, doc.id)
        self.assertEqual(entry.name, doc.name)
        self.assertEqual(entry.category, doc.category)
        self.assertEqual(entry.severity, doc.severity.value)

    def test_severity_index(self):
        """Test severity secondary index."""
        doc1 = create_test_document(
            "reentrancy/classic/doc1", severity=Severity.CRITICAL
        )
        doc2 = create_test_document(
            "reentrancy/classic/doc2", severity=Severity.HIGH
        )

        self.store.save(doc1)
        self.store.save(doc2)

        index = self.builder.build()

        critical_docs = index.get_by_severity("critical")
        self.assertEqual(len(critical_docs), 1)
        self.assertEqual(critical_docs[0], doc1.id)

    def test_keyword_index(self):
        """Test keyword secondary index."""
        doc1 = create_test_document(
            "reentrancy/classic/doc1", keywords=["reentrancy", "callback"]
        )
        doc2 = create_test_document(
            "reentrancy/classic/doc2", keywords=["cross-function"]
        )

        self.store.save(doc1)
        self.store.save(doc2)

        index = self.builder.build()

        docs = index.get_by_keyword("reentrancy")
        self.assertEqual(len(docs), 1)
        self.assertEqual(docs[0], doc1.id)

    def test_pattern_index(self):
        """Test pattern secondary index."""
        doc1 = create_test_document(
            "reentrancy/classic/doc1", pattern_ids=["reentrancy-001"]
        )
        doc2 = create_test_document(
            "reentrancy/classic/doc2", pattern_ids=["reentrancy-002"]
        )

        self.store.save(doc1)
        self.store.save(doc2)

        index = self.builder.build()

        docs = index.get_by_pattern("reentrancy-001")
        self.assertEqual(len(docs), 1)
        self.assertEqual(docs[0], doc1.id)

    def test_subcategory_index(self):
        """Test subcategory secondary index."""
        doc1 = create_test_document("reentrancy/classic/doc1")
        doc2 = create_test_document("reentrancy/cross-function/doc1",
                                     subcategory="cross-function")

        self.store.save(doc1)
        self.store.save(doc2)

        index = self.builder.build()

        docs = index.get_by_subcategory("reentrancy", "classic")
        self.assertEqual(len(docs), 1)
        self.assertEqual(docs[0], doc1.id)

    def test_category_summary(self):
        """Test category summary generation."""
        doc1 = create_test_document(
            "reentrancy/classic/doc1", severity=Severity.CRITICAL
        )
        doc2 = create_test_document(
            "reentrancy/classic/doc2", severity=Severity.HIGH
        )

        self.store.save(doc1)
        self.store.save(doc2)

        index = self.builder.build()
        summary = index.get_category("reentrancy")

        self.assertIsNotNone(summary)
        self.assertEqual(summary.document_count, 2)
        self.assertIn("classic", summary.subcategories)
        self.assertIn("critical", summary.severity_distribution)

    def test_update_entry(self):
        """Test updating a single entry."""
        doc = create_test_document()
        self.store.save(doc)
        self.builder.build()

        # Update document
        doc.name = "Updated Name"
        self.store.save(doc)
        self.builder.update_entry(doc)

        entry = self.builder.get_index().get_entry(doc.id)
        self.assertEqual(entry.name, "Updated Name")

    def test_remove_entry(self):
        """Test removing an entry."""
        doc = create_test_document()
        self.store.save(doc)
        index = self.builder.build()

        self.assertIsNotNone(index.get_entry(doc.id))

        result = self.builder.remove_entry(doc.id)
        self.assertTrue(result)
        self.assertIsNone(self.builder.get_index().get_entry(doc.id))

    def test_save_and_load_index(self):
        """Test saving and loading index."""
        doc = create_test_document()
        self.store.save(doc)
        self.builder.build()

        # Save
        index_path = self.builder.save_index()
        self.assertTrue(Path(index_path).exists())

        # Create new builder and load
        new_builder = IndexBuilder(self.store)
        loaded_index = new_builder.load_index()

        self.assertEqual(loaded_index.total_documents, 1)
        self.assertIsNotNone(loaded_index.get_entry(doc.id))

    def test_search_index(self):
        """Test searching the index."""
        doc1 = create_test_document(
            "reentrancy/classic/doc1",
            name="Classic Reentrancy",
            keywords=["callback", "external-call"],
        )
        doc2 = create_test_document(
            "access-control/missing-modifier/doc1",
            category="access-control",
            subcategory="missing-modifier",
            name="Missing Access Control",
            keywords=["authorization", "modifier"],
        )

        self.store.save(doc1)
        self.store.save(doc2)

        index = self.builder.build()

        # Search for "Classic" which only appears in doc1's name
        results = index.search("Classic")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].name, "Classic Reentrancy")

    def test_navigation_context(self):
        """Test generating navigation context."""
        doc = create_test_document()
        self.store.save(doc)
        self.builder.build()

        context = self.builder.get_navigation_context()

        self.assertIn("VulnDocs Knowledge Base", context)
        self.assertIn("Categories", context)

    def test_category_index(self):
        """Test generating category index."""
        doc = create_test_document()
        self.store.save(doc)
        self.builder.build()

        context = self.builder.get_category_index("reentrancy")

        self.assertIn("Reentrancy", context)
        self.assertIn("classic", context)


class TestKnowledgeRetriever(unittest.TestCase):
    """Tests for KnowledgeRetriever."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.config = StorageConfig(base_path=self.temp_dir)
        self.store = KnowledgeStore(self.config)
        self.retriever = KnowledgeRetriever(self.store)

    def tearDown(self):
        """Clean up after tests."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_get_document(self):
        """Test retrieving a specific document."""
        doc = create_test_document()
        self.store.save(doc)

        result = self.retriever.get_document(doc.id)

        self.assertEqual(result.result_count, 1)
        self.assertEqual(result.documents[0].id, doc.id)
        self.assertIn(doc.name, result.context)

    def test_get_by_category(self):
        """Test retrieving by category."""
        doc1 = create_test_document("reentrancy/classic/doc1")
        doc2 = create_test_document("reentrancy/classic/doc2")

        self.store.save(doc1)
        self.store.save(doc2)

        result = self.retriever.get_by_category("reentrancy")

        self.assertEqual(result.result_count, 2)
        self.assertEqual(result.query_type, "category")

    def test_get_by_subcategory(self):
        """Test retrieving by subcategory."""
        doc1 = create_test_document("reentrancy/classic/doc1")
        doc2 = create_test_document("reentrancy/cross-function/doc1",
                                     subcategory="cross-function")

        self.store.save(doc1)
        self.store.save(doc2)

        result = self.retriever.get_by_category("reentrancy", "classic")

        self.assertEqual(result.result_count, 1)
        self.assertEqual(result.documents[0].subcategory, "classic")

    def test_search_keywords(self):
        """Test keyword search."""
        doc1 = create_test_document(
            "reentrancy/classic/doc1",
            keywords=["reentrancy", "callback"],
        )
        doc2 = create_test_document(
            "access-control/missing-modifier/doc1",
            category="access-control",
            subcategory="missing-modifier",
            keywords=["access", "modifier"],
        )

        self.store.save(doc1)
        self.store.save(doc2)

        result = self.retriever.search("reentrancy")

        self.assertGreaterEqual(result.result_count, 1)
        self.assertEqual(result.query_type, "search")

    def test_search_multiple_keywords(self):
        """Test search with multiple keywords."""
        doc = create_test_document(
            "reentrancy/classic/doc1",
            keywords=["reentrancy", "callback", "state-update"],
        )
        self.store.save(doc)

        result = self.retriever.search(["reentrancy", "callback"])

        self.assertEqual(result.result_count, 1)

    def test_get_by_pattern(self):
        """Test retrieving by pattern ID."""
        doc = create_test_document(
            "reentrancy/classic/doc1",
            pattern_ids=["reentrancy-001", "reentrancy-002"],
        )
        self.store.save(doc)

        result = self.retriever.get_by_pattern("reentrancy-001")

        self.assertEqual(result.result_count, 1)
        self.assertEqual(result.query_type, "pattern")

    def test_retrieval_depth_minimal(self):
        """Test minimal retrieval depth."""
        doc = create_test_document()
        self.store.save(doc)

        result = self.retriever.get_document(doc.id, depth=RetrievalDepth.MINIMAL)

        self.assertIn(doc.name, result.context)
        self.assertIn(doc.severity.value, result.context)
        # Should not include full sections
        self.assertNotIn("Attack Steps", result.context)

    def test_retrieval_depth_full(self):
        """Test full retrieval depth."""
        doc = create_test_document()
        self.store.save(doc)

        result = self.retriever.get_document(doc.id, depth=RetrievalDepth.FULL)

        self.assertIn(doc.name, result.context)
        self.assertIn("Detection", result.context)
        self.assertIn("Mitigation", result.context)

    def test_retrieval_depth_compact(self):
        """Test compact retrieval depth."""
        doc = create_test_document()
        self.store.save(doc)

        result = self.retriever.get_document(doc.id, depth=RetrievalDepth.COMPACT)

        # Compact format should be shorter
        full_result = self.retriever.get_document(doc.id, depth=RetrievalDepth.FULL)
        self.assertLess(len(result.context), len(full_result.context))

    def test_token_budget(self):
        """Test token budget limiting."""
        # Create many documents
        for i in range(10):
            doc = create_test_document(f"reentrancy/classic/doc{i}")
            self.store.save(doc)

        result = self.retriever.get_by_category(
            "reentrancy",
            depth=RetrievalDepth.STANDARD,
            max_results=10,
        )

        # Token estimate should be present
        self.assertGreater(result.token_estimate, 0)

    def test_get_context_for_finding(self):
        """Test getting context for a finding."""
        doc = create_test_document(pattern_ids=["reentrancy-001"])
        self.store.save(doc)

        finding = {
            "category": "reentrancy",
            "pattern_id": "reentrancy-001",
            "signals": ["state_write_after_external_call"],
        }

        context = self.retriever.get_context_for_finding(finding)

        self.assertIn("reentrancy", context.lower())

    def test_get_navigation_context(self):
        """Test getting navigation context."""
        doc = create_test_document()
        self.store.save(doc)

        context = self.retriever.get_navigation_context()

        self.assertIn("Navigation", context)
        self.assertIn("Categories", context)

    def test_list_categories(self):
        """Test listing categories."""
        doc1 = create_test_document("reentrancy/classic/doc1")
        doc2 = create_test_document(
            "access-control/missing-modifier/doc1",
            category="access-control",
            subcategory="missing-modifier",
        )

        self.store.save(doc1)
        self.store.save(doc2)

        categories = self.retriever.list_categories()

        self.assertIn("reentrancy", categories)
        self.assertIn("access-control", categories)

    def test_list_subcategories(self):
        """Test listing subcategories."""
        doc1 = create_test_document("reentrancy/classic/doc1")
        doc2 = create_test_document(
            "reentrancy/cross-function/doc1",
            subcategory="cross-function",
        )

        self.store.save(doc1)
        self.store.save(doc2)

        subcategories = self.retriever.list_subcategories("reentrancy")

        self.assertIn("classic", subcategories)
        self.assertIn("cross-function", subcategories)

    def test_get_stats(self):
        """Test getting retrieval stats."""
        doc = create_test_document()
        self.store.save(doc)

        stats = self.retriever.get_stats()

        self.assertEqual(stats["total_documents"], 1)
        self.assertIn("reentrancy", stats["categories"])

    def test_severity_filter(self):
        """Test filtering by severity."""
        doc1 = create_test_document(
            "reentrancy/classic/doc1",
            severity=Severity.CRITICAL,
        )
        doc2 = create_test_document(
            "reentrancy/classic/doc2",
            severity=Severity.LOW,
        )

        self.store.save(doc1)
        self.store.save(doc2)

        result = self.retriever.search(
            "test",
            severity_filter="critical",
        )

        # Should only return critical severity
        for doc in result.documents:
            self.assertEqual(doc.severity, Severity.CRITICAL)

    def test_retrieval_query_builders(self):
        """Test RetrievalQuery class methods."""
        # by_category
        query = RetrievalQuery.by_category("reentrancy", "classic")
        self.assertEqual(query.category, "reentrancy")
        self.assertEqual(query.subcategory, "classic")

        # by_doc_id
        query = RetrievalQuery.by_doc_id("reentrancy/classic/doc1")
        self.assertEqual(query.doc_id, "reentrancy/classic/doc1")
        self.assertEqual(query.depth, RetrievalDepth.FULL)

        # by_keywords
        query = RetrievalQuery.by_keywords(["test", "vuln"])
        self.assertEqual(query.keywords, ["test", "vuln"])

        # by_pattern
        query = RetrievalQuery.by_pattern(["reentrancy-001"])
        self.assertEqual(query.pattern_ids, ["reentrancy-001"])

    def test_retrieval_result_methods(self):
        """Test RetrievalResult methods."""
        doc = create_test_document()
        self.store.save(doc)

        result = self.retriever.get_document(doc.id)

        # get_first
        first = result.get_first()
        self.assertEqual(first.id, doc.id)

        # get_context
        context = result.get_context()
        self.assertIn(doc.name, context)

        # to_dict
        data = result.to_dict()
        self.assertEqual(data["result_count"], 1)


class TestIndexEntry(unittest.TestCase):
    """Tests for IndexEntry serialization."""

    def test_to_dict_from_dict(self):
        """Test serialization round-trip."""
        entry = IndexEntry(
            doc_id="reentrancy/classic/doc1",
            name="Test Doc",
            category="reentrancy",
            subcategory="classic",
            severity="high",
            one_liner="Test description",
            keywords=["test", "keyword"],
            pattern_ids=["pattern-001"],
            linkage_type="exact_match",
            token_estimate=500,
            content_hash="abc123",
            last_updated="2026-01-08",
        )

        data = entry.to_dict()
        loaded = IndexEntry.from_dict(data)

        self.assertEqual(loaded.doc_id, entry.doc_id)
        self.assertEqual(loaded.keywords, entry.keywords)
        self.assertEqual(loaded.pattern_ids, entry.pattern_ids)


class TestCategorySummary(unittest.TestCase):
    """Tests for CategorySummary serialization."""

    def test_to_dict_from_dict(self):
        """Test serialization round-trip."""
        summary = CategorySummary(
            name="reentrancy",
            display_name="Reentrancy",
            description="Test description",
            subcategory_count=5,
            document_count=10,
            total_tokens=5000,
            subcategories=["classic", "cross-function"],
            severity_distribution={"critical": 3, "high": 7},
            pattern_coverage=0.8,
        )

        data = summary.to_dict()
        loaded = CategorySummary.from_dict(data)

        self.assertEqual(loaded.name, summary.name)
        self.assertEqual(loaded.subcategories, summary.subcategories)
        self.assertEqual(loaded.pattern_coverage, summary.pattern_coverage)


class TestKnowledgeIndex(unittest.TestCase):
    """Tests for KnowledgeIndex."""

    def test_to_dict_from_dict(self):
        """Test serialization round-trip."""
        index = KnowledgeIndex(
            total_documents=10,
            total_categories=3,
            total_tokens=5000,
        )

        data = index.to_dict()
        loaded = KnowledgeIndex.from_dict(data)

        self.assertEqual(loaded.total_documents, index.total_documents)
        self.assertEqual(loaded.total_categories, index.total_categories)


if __name__ == "__main__":
    unittest.main()
