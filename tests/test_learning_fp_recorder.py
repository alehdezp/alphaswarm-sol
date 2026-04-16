"""Tests for false positive recorder.

Task 7.4: FP recording and warning system.
"""

from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock

from alphaswarm_sol.learning.fp_recorder import (
    FPPattern,
    FPWarning,
    FalsePositiveRecorder,
)
from alphaswarm_sol.learning.types import SimilarityTier


class TestFPPattern(unittest.TestCase):
    """Test FPPattern dataclass."""

    def test_create_basic(self):
        """Create basic FP pattern."""
        pattern = FPPattern(
            pattern_id="vm-001",
            modifier_signature="nonReentrant",
            guard_patterns={"REENTRANCY_GUARD"},
        )
        self.assertEqual(pattern.pattern_id, "vm-001")
        self.assertEqual(pattern.modifier_signature, "nonReentrant")
        self.assertIn("REENTRANCY_GUARD", pattern.guard_patterns)
        self.assertEqual(pattern.occurrence_count, 0)

    def test_matches_pattern_only(self):
        """Pattern tier matches on pattern_id only."""
        pattern = FPPattern(
            pattern_id="vm-001",
            modifier_signature="nonReentrant|onlyOwner",
            guard_patterns={"REENTRANCY_GUARD"},
        )

        finding = Mock()
        finding.pattern_id = "vm-001"
        finding.modifiers = []  # Different modifiers

        self.assertTrue(pattern.matches(finding, SimilarityTier.PATTERN))

    def test_matches_pattern_different_id(self):
        """Pattern tier fails on different pattern_id."""
        pattern = FPPattern(
            pattern_id="vm-001",
            modifier_signature="",
            guard_patterns=set(),
        )

        finding = Mock()
        finding.pattern_id = "vm-002"  # Different
        finding.modifiers = []

        self.assertFalse(pattern.matches(finding, SimilarityTier.PATTERN))

    def test_matches_structural_same_modifiers(self):
        """Structural tier matches when modifiers are subset."""
        pattern = FPPattern(
            pattern_id="vm-001",
            modifier_signature="nonReentrant",
            guard_patterns=set(),
        )

        finding = Mock()
        finding.pattern_id = "vm-001"
        finding.modifiers = ["nonReentrant", "onlyOwner"]  # Superset

        self.assertTrue(pattern.matches(finding, SimilarityTier.STRUCTURAL))

    def test_matches_structural_missing_modifiers(self):
        """Structural tier fails when modifiers missing."""
        pattern = FPPattern(
            pattern_id="vm-001",
            modifier_signature="nonReentrant|onlyOwner",
            guard_patterns=set(),
        )

        finding = Mock()
        finding.pattern_id = "vm-001"
        finding.modifiers = ["nonReentrant"]  # Missing onlyOwner

        self.assertFalse(pattern.matches(finding, SimilarityTier.STRUCTURAL))

    def test_matches_structural_empty_both(self):
        """Structural tier matches when both have no modifiers."""
        pattern = FPPattern(
            pattern_id="vm-001",
            modifier_signature="",
            guard_patterns=set(),
        )

        finding = Mock()
        finding.pattern_id = "vm-001"
        finding.modifiers = []

        self.assertTrue(pattern.matches(finding, SimilarityTier.STRUCTURAL))

    def test_to_dict(self):
        """Convert to dict."""
        now = datetime.now()
        pattern = FPPattern(
            pattern_id="vm-001",
            modifier_signature="mod1|mod2",
            guard_patterns={"GUARD1", "GUARD2"},
            occurrence_count=5,
            last_seen=now,
            first_seen=now,
            reasons=["reason1", "reason2"],
        )
        d = pattern.to_dict()
        self.assertEqual(d["pattern_id"], "vm-001")
        self.assertEqual(d["modifier_signature"], "mod1|mod2")
        self.assertEqual(set(d["guard_patterns"]), {"GUARD1", "GUARD2"})
        self.assertEqual(d["occurrence_count"], 5)
        self.assertEqual(d["reasons"], ["reason1", "reason2"])

    def test_from_dict(self):
        """Create from dict."""
        data = {
            "pattern_id": "vm-002",
            "modifier_signature": "guard1",
            "guard_patterns": ["PATTERN1"],
            "occurrence_count": 3,
            "last_seen": "2026-01-08T12:00:00",
            "first_seen": "2026-01-01T12:00:00",
            "reasons": ["test reason"],
        }
        pattern = FPPattern.from_dict(data)
        self.assertEqual(pattern.pattern_id, "vm-002")
        self.assertEqual(pattern.occurrence_count, 3)
        self.assertEqual(pattern.guard_patterns, {"PATTERN1"})

    def test_round_trip(self):
        """Dict round-trip preserves data."""
        pattern = FPPattern(
            pattern_id="oracle-001",
            modifier_signature="staleness",
            guard_patterns={"STALENESS_CHECK"},
            occurrence_count=10,
            reasons=["Has staleness check", "Uses Chainlink"],
        )
        restored = FPPattern.from_dict(pattern.to_dict())
        self.assertEqual(restored.pattern_id, pattern.pattern_id)
        self.assertEqual(restored.modifier_signature, pattern.modifier_signature)
        self.assertEqual(restored.guard_patterns, pattern.guard_patterns)
        self.assertEqual(restored.occurrence_count, pattern.occurrence_count)
        self.assertEqual(restored.reasons, pattern.reasons)


class TestFPWarning(unittest.TestCase):
    """Test FPWarning dataclass."""

    def test_create_warning(self):
        """Create warning."""
        warning = FPWarning(
            level="likely",
            message="Test message",
            occurrence_count=6,
            reasons=["reason1"],
            pattern_id="vm-001",
            modifier_signature="nonReentrant",
        )
        self.assertEqual(warning.level, "likely")
        self.assertEqual(warning.occurrence_count, 6)

    def test_to_dict(self):
        """Convert to dict."""
        warning = FPWarning(
            level="possible",
            message="Check this",
            occurrence_count=3,
            reasons=["r1", "r2"],
            pattern_id="dos-001",
            modifier_signature="",
        )
        d = warning.to_dict()
        self.assertEqual(d["level"], "possible")
        self.assertEqual(d["occurrence_count"], 3)
        self.assertEqual(d["reasons"], ["r1", "r2"])


class TestFalsePositiveRecorder(unittest.TestCase):
    """Test FalsePositiveRecorder class."""

    def setUp(self):
        """Set up test storage."""
        self.temp_dir = tempfile.mkdtemp()
        self.recorder = FalsePositiveRecorder(Path(self.temp_dir))

    def tearDown(self):
        """Clean up temp directory."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _create_finding(
        self,
        pattern_id: str = "vm-001",
        modifiers: list = None,
    ) -> Mock:
        """Create mock finding."""
        finding = Mock()
        finding.pattern_id = pattern_id
        finding.modifiers = modifiers or []
        return finding

    def test_record_single(self):
        """Record single FP."""
        finding = self._create_finding()
        key = self.recorder.record(finding, "Test reason")

        self.assertIn(key, self.recorder._fp_patterns)
        self.assertEqual(self.recorder._fp_patterns[key].occurrence_count, 1)

    def test_record_multiple(self):
        """Record multiple FPs for same pattern."""
        finding = self._create_finding()
        self.recorder.record(finding, "Reason 1")
        self.recorder.record(finding, "Reason 2")
        key = self.recorder.record(finding, "Reason 3")

        self.assertEqual(self.recorder._fp_patterns[key].occurrence_count, 3)
        self.assertEqual(len(self.recorder._fp_patterns[key].reasons), 3)

    def test_record_no_duplicate_reasons(self):
        """Don't store duplicate reasons."""
        finding = self._create_finding()
        self.recorder.record(finding, "Same reason")
        self.recorder.record(finding, "Same reason")
        key = self.recorder.record(finding, "Same reason")

        self.assertEqual(len(self.recorder._fp_patterns[key].reasons), 1)

    def test_no_warning_single_occurrence(self):
        """No warning for single occurrence."""
        finding = self._create_finding()
        self.recorder.record(finding, "Some reason")

        warnings = self.recorder.get_warnings(finding)
        self.assertEqual(len(warnings), 0)

    def test_possible_warning(self):
        """Get possible warning at threshold."""
        finding = self._create_finding(modifiers=["nonReentrant"])

        # Record 2 FPs (default threshold)
        self.recorder.record(finding, "Has reentrancy guard")
        self.recorder.record(finding, "Has reentrancy guard")

        warnings = self.recorder.get_warnings(finding)
        self.assertEqual(len(warnings), 1)
        self.assertEqual(warnings[0].level, "possible")
        self.assertIn("similar", warnings[0].message.lower())

    def test_likely_warning(self):
        """Get likely warning at strong threshold."""
        finding = self._create_finding(modifiers=["nonReentrant"])

        # Record 6 FPs (above strong threshold of 5)
        for _ in range(6):
            self.recorder.record(finding, "Has guard")

        warnings = self.recorder.get_warnings(finding)
        self.assertEqual(len(warnings), 1)
        self.assertEqual(warnings[0].level, "likely")
        self.assertIn("LIKELY", warnings[0].message)

    def test_warning_string_convenience(self):
        """Get warning strings convenience method."""
        finding = self._create_finding()
        self.recorder.record(finding, "Reason")
        self.recorder.record(finding, "Reason")

        strings = self.recorder.get_warning_strings(finding)
        self.assertEqual(len(strings), 1)
        self.assertIsInstance(strings[0], str)

    def test_warning_different_modifiers(self):
        """Different modifiers don't trigger warning."""
        finding1 = self._create_finding(modifiers=["nonReentrant"])
        finding2 = self._create_finding(modifiers=["onlyOwner"])

        # Record FPs for finding1
        for _ in range(5):
            self.recorder.record(finding1, "Has guard")

        # finding2 should not get warning
        warnings = self.recorder.get_warnings(finding2)
        self.assertEqual(len(warnings), 0)

    def test_get_fp_count(self):
        """Get total FP count for pattern."""
        finding1 = self._create_finding("vm-001", ["mod1"])
        finding2 = self._create_finding("vm-001", ["mod2"])

        for _ in range(3):
            self.recorder.record(finding1, "reason")
        for _ in range(2):
            self.recorder.record(finding2, "reason")

        count = self.recorder.get_fp_count("vm-001")
        self.assertEqual(count, 5)

    def test_get_fp_patterns_for(self):
        """Get FP patterns for a pattern_id."""
        finding1 = self._create_finding("vm-001", ["mod1"])
        finding2 = self._create_finding("vm-001", ["mod2"])
        finding3 = self._create_finding("vm-002", [])

        self.recorder.record(finding1, "r1")
        self.recorder.record(finding2, "r2")
        self.recorder.record(finding3, "r3")

        patterns = self.recorder.get_fp_patterns_for("vm-001")
        self.assertEqual(len(patterns), 2)

    def test_clear_pattern(self):
        """Clear FPs for a pattern."""
        finding1 = self._create_finding("vm-001")
        finding2 = self._create_finding("vm-002")

        self.recorder.record(finding1, "r1")
        self.recorder.record(finding1, "r1")
        self.recorder.record(finding2, "r2")

        cleared = self.recorder.clear_pattern("vm-001")
        self.assertEqual(cleared, 1)
        self.assertEqual(self.recorder.get_fp_count("vm-001"), 0)
        self.assertEqual(self.recorder.get_fp_count("vm-002"), 1)

    def test_persistence(self):
        """FP patterns persist across instances."""
        finding = self._create_finding()
        self.recorder.record(finding, "Persistent reason")
        self.recorder.record(finding, "Persistent reason")

        # Create new recorder
        new_recorder = FalsePositiveRecorder(Path(self.temp_dir))
        self.assertEqual(new_recorder.get_fp_count("vm-001"), 2)

    def test_summary(self):
        """Generate summary."""
        finding1 = self._create_finding("vm-001", ["guard1"])
        finding2 = self._create_finding("oracle-001", [])

        for _ in range(3):
            self.recorder.record(finding1, "Has guard")
        self.recorder.record(finding2, "Has staleness check")

        summary = self.recorder.summary()
        self.assertIn("vm-001", summary)
        self.assertIn("oracle-001", summary)
        self.assertIn("Has guard", summary)

    def test_summary_empty(self):
        """Summary for empty recorder."""
        summary = self.recorder.summary()
        self.assertIn("No FP patterns", summary)

    def test_to_dict_export(self):
        """Export all data as dict."""
        finding = self._create_finding()
        self.recorder.record(finding, "r1")
        self.recorder.record(finding, "r2")

        data = self.recorder.to_dict()
        self.assertIn("patterns", data)
        self.assertEqual(data["total_fps"], 2)
        self.assertEqual(data["pattern_count"], 1)

    def test_custom_thresholds(self):
        """Custom warning thresholds."""
        recorder = FalsePositiveRecorder(
            Path(self.temp_dir) / "custom",
            min_warning_threshold=3,
            strong_warning_threshold=10,
        )
        finding = self._create_finding()

        # 2 occurrences - no warning with threshold 3
        recorder.record(finding, "r1")
        recorder.record(finding, "r2")
        warnings = recorder.get_warnings(finding)
        self.assertEqual(len(warnings), 0)

        # 3 occurrences - possible warning
        recorder.record(finding, "r3")
        warnings = recorder.get_warnings(finding)
        self.assertEqual(len(warnings), 1)
        self.assertEqual(warnings[0].level, "possible")


class TestDecayOldPatterns(unittest.TestCase):
    """Test decay functionality for old patterns."""

    def setUp(self):
        """Set up test storage."""
        self.temp_dir = tempfile.mkdtemp()
        self.recorder = FalsePositiveRecorder(Path(self.temp_dir))

    def tearDown(self):
        """Clean up."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_decay_old_patterns(self):
        """Remove patterns older than threshold."""
        finding = Mock()
        finding.pattern_id = "vm-001"
        finding.modifiers = []

        # Record FP
        self.recorder.record(finding, "test")

        # Manually set last_seen to old date
        key = list(self.recorder._fp_patterns.keys())[0]
        self.recorder._fp_patterns[key].last_seen = datetime.now() - timedelta(days=200)
        self.recorder._save()

        # Decay
        removed = self.recorder.decay_old_patterns(max_age_days=180)
        self.assertEqual(removed, 1)
        self.assertEqual(len(self.recorder._fp_patterns), 0)

    def test_decay_keeps_recent(self):
        """Keep recent patterns."""
        finding = Mock()
        finding.pattern_id = "vm-001"
        finding.modifiers = []

        self.recorder.record(finding, "test")

        # Should not remove recent pattern
        removed = self.recorder.decay_old_patterns(max_age_days=180)
        self.assertEqual(removed, 0)
        self.assertEqual(len(self.recorder._fp_patterns), 1)


class TestGuardPatterns(unittest.TestCase):
    """Test guard pattern handling."""

    def setUp(self):
        """Set up test storage."""
        self.temp_dir = tempfile.mkdtemp()
        self.recorder = FalsePositiveRecorder(Path(self.temp_dir))

    def tearDown(self):
        """Clean up."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_record_with_guard_patterns(self):
        """Record FP with guard patterns."""
        finding = Mock()
        finding.pattern_id = "vm-001"
        finding.modifiers = ["nonReentrant"]

        key = self.recorder.record(
            finding,
            "Has reentrancy guard",
            guard_patterns=["REENTRANCY_GUARD", "MUTEX"],
        )

        pattern = self.recorder._fp_patterns[key]
        self.assertIn("REENTRANCY_GUARD", pattern.guard_patterns)
        self.assertIn("MUTEX", pattern.guard_patterns)

    def test_guard_patterns_accumulate(self):
        """Guard patterns accumulate across recordings."""
        finding = Mock()
        finding.pattern_id = "vm-001"
        finding.modifiers = []

        self.recorder.record(finding, "r1", guard_patterns=["GUARD1"])
        key = self.recorder.record(finding, "r2", guard_patterns=["GUARD2"])

        pattern = self.recorder._fp_patterns[key]
        self.assertEqual(pattern.guard_patterns, {"GUARD1", "GUARD2"})


class TestEdgeCases(unittest.TestCase):
    """Test edge cases."""

    def setUp(self):
        """Set up test storage."""
        self.temp_dir = tempfile.mkdtemp()
        self.recorder = FalsePositiveRecorder(Path(self.temp_dir))

    def tearDown(self):
        """Clean up."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_empty_reason(self):
        """Handle empty reason."""
        finding = Mock()
        finding.pattern_id = "vm-001"
        finding.modifiers = []

        key = self.recorder.record(finding, "")
        self.assertEqual(len(self.recorder._fp_patterns[key].reasons), 0)

    def test_missing_modifiers_attribute(self):
        """Handle finding without modifiers attribute."""
        finding = Mock(spec=["pattern_id"])
        finding.pattern_id = "vm-001"

        # Should not raise
        key = self.recorder.record(finding, "test")
        self.assertIn(key, self.recorder._fp_patterns)

    def test_max_reasons_limit(self):
        """Respect max reasons limit."""
        finding = Mock()
        finding.pattern_id = "vm-001"
        finding.modifiers = []

        for i in range(15):
            self.recorder.record(finding, f"reason_{i}")

        key = list(self.recorder._fp_patterns.keys())[0]
        self.assertLessEqual(
            len(self.recorder._fp_patterns[key].reasons),
            FalsePositiveRecorder.MAX_REASONS,
        )

    def test_corrupted_storage(self):
        """Handle corrupted storage file."""
        # Write corrupted data
        fp_file = Path(self.temp_dir) / "fp_patterns.json"
        with open(fp_file, "w") as f:
            f.write("invalid json {{{")

        # Should create new recorder without crashing
        recorder = FalsePositiveRecorder(Path(self.temp_dir))
        self.assertEqual(len(recorder._fp_patterns), 0)


if __name__ == "__main__":
    unittest.main()
