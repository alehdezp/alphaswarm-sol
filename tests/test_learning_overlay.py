"""Tests for learning overlay storage."""

from __future__ import annotations

import shutil
import tempfile
import unittest
from pathlib import Path

from alphaswarm_sol.learning.overlay import LearningOverlayStore, format_overlay_context


class TestLearningOverlayStore(unittest.TestCase):
    """Tests for overlay storage and retrieval."""

    def setUp(self) -> None:
        self.temp_dir = Path(tempfile.mkdtemp())
        self.store = LearningOverlayStore(self.temp_dir)

    def tearDown(self) -> None:
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_record_label_and_get(self):
        """Record a label and retrieve it."""
        recorded = self.store.record_label(
            node_id="function:abc",
            label="IS_REENTRANCY_GUARD",
            pattern_id="vm-001",
            bead_id="VKG-0001",
            confidence=0.95,
        )
        self.assertTrue(recorded)
        labels = self.store.get_labels("function:abc", category="reentrancy")
        self.assertEqual(len(labels), 1)
        self.assertEqual(labels[0].label, "IS_REENTRANCY_GUARD")

    def test_category_filter(self):
        """Labels are filtered by category relevance."""
        self.store.record_label(
            node_id="function:abc",
            label="IS_REENTRANCY_GUARD",
            pattern_id="vm-001",
            bead_id="VKG-0001",
            confidence=0.95,
        )
        labels = self.store.get_labels("function:abc", category="oracle")
        self.assertEqual(labels, [])

    def test_record_edge_and_get(self):
        """Record an edge and retrieve it."""
        recorded = self.store.record_edge(
            source_id="function:guard",
            target_id="function:target",
            relation="GUARDS",
            pattern_id="vm-001",
            bead_id="VKG-0002",
            confidence=0.9,
        )
        self.assertTrue(recorded)
        edges = self.store.get_edges("function:guard", category="reentrancy")
        self.assertEqual(len(edges), 1)
        self.assertEqual(edges[0].label, "GUARDS")

    def test_format_overlay_context(self):
        """Overlay context formatting is stable."""
        self.store.record_label(
            node_id="function:abc",
            label="IS_REENTRANCY_GUARD",
            pattern_id="vm-001",
            bead_id="VKG-0001",
            confidence=0.95,
        )
        labels = self.store.get_labels("function:abc", category="reentrancy")
        context = format_overlay_context(labels, [], [])
        self.assertIn("Learned Labels", context)
        self.assertIn("IS_REENTRANCY_GUARD", context)
