"""
Tests for Pragma Compatibility Check (Task 4.4)

Validates version parsing, range operations, and compatibility checking.
"""

import tempfile
import unittest
from pathlib import Path

from alphaswarm_sol.testing.pragma import (
    SemVer,
    VersionRange,
    CompatibilityStatus,
    CompatibilityResult,
    parse_pragma,
    check_pragma_compatibility,
    suggest_test_pragma,
    get_pragma_from_file,
    find_common_pragma,
)


class TestSemVer(unittest.TestCase):
    """Tests for SemVer class."""

    def test_parse_full_version(self):
        """Parse full major.minor.patch version."""
        v = SemVer.parse("0.8.20")
        self.assertIsNotNone(v)
        self.assertEqual(v.major, 0)
        self.assertEqual(v.minor, 8)
        self.assertEqual(v.patch, 20)

    def test_parse_minor_only(self):
        """Parse major.minor version (patch defaults to 0)."""
        v = SemVer.parse("0.8")
        self.assertIsNotNone(v)
        self.assertEqual(v.major, 0)
        self.assertEqual(v.minor, 8)
        self.assertEqual(v.patch, 0)

    def test_parse_major_only(self):
        """Parse major-only version."""
        v = SemVer.parse("1")
        self.assertIsNotNone(v)
        self.assertEqual(v.major, 1)
        self.assertEqual(v.minor, 0)
        self.assertEqual(v.patch, 0)

    def test_parse_invalid(self):
        """Return None for invalid version."""
        self.assertIsNone(SemVer.parse("invalid"))
        self.assertIsNone(SemVer.parse("1.2.3.4"))
        self.assertIsNone(SemVer.parse(""))

    def test_comparison_less_than(self):
        """Test less than comparison."""
        v1 = SemVer.parse("0.8.0")
        v2 = SemVer.parse("0.8.20")
        self.assertTrue(v1 < v2)
        self.assertFalse(v2 < v1)

    def test_comparison_equal(self):
        """Test equality comparison."""
        v1 = SemVer.parse("0.8.20")
        v2 = SemVer.parse("0.8.20")
        self.assertEqual(v1, v2)

    def test_comparison_minor_precedence(self):
        """Minor version takes precedence over patch."""
        v1 = SemVer.parse("0.8.99")
        v2 = SemVer.parse("0.9.0")
        self.assertTrue(v1 < v2)

    def test_str_representation(self):
        """String representation is version format."""
        v = SemVer.parse("0.8.20")
        self.assertEqual(str(v), "0.8.20")

    def test_bump_minor(self):
        """Bump minor increments minor and zeros patch."""
        v = SemVer.parse("0.8.20")
        bumped = v.bump_minor()
        self.assertEqual(bumped.major, 0)
        self.assertEqual(bumped.minor, 9)
        self.assertEqual(bumped.patch, 0)


class TestVersionRange(unittest.TestCase):
    """Tests for VersionRange class."""

    def test_contains_within_range(self):
        """Version within range is contained."""
        r = VersionRange(
            min_version=SemVer(0, 8, 0),
            max_version=SemVer(0, 9, 0),
            min_inclusive=True,
            max_inclusive=False,
        )
        self.assertTrue(r.contains(SemVer(0, 8, 10)))
        self.assertTrue(r.contains(SemVer(0, 8, 0)))  # Min inclusive
        self.assertFalse(r.contains(SemVer(0, 9, 0)))  # Max exclusive

    def test_contains_at_boundaries(self):
        """Test boundary inclusion/exclusion."""
        r = VersionRange(
            min_version=SemVer(0, 8, 0),
            max_version=SemVer(0, 9, 0),
            min_inclusive=False,
            max_inclusive=True,
        )
        self.assertFalse(r.contains(SemVer(0, 8, 0)))  # Min exclusive
        self.assertTrue(r.contains(SemVer(0, 9, 0)))  # Max inclusive

    def test_overlaps_true(self):
        """Ranges that overlap return True."""
        r1 = VersionRange(
            min_version=SemVer(0, 8, 0),
            max_version=SemVer(0, 9, 0),
        )
        r2 = VersionRange(
            min_version=SemVer(0, 8, 10),
            max_version=SemVer(0, 8, 20),
        )
        self.assertTrue(r1.overlaps(r2))
        self.assertTrue(r2.overlaps(r1))

    def test_overlaps_false(self):
        """Non-overlapping ranges return False."""
        r1 = VersionRange(
            min_version=SemVer(0, 7, 0),
            max_version=SemVer(0, 8, 0),
            max_inclusive=False,
        )
        r2 = VersionRange(
            min_version=SemVer(0, 8, 0),
            max_version=SemVer(0, 9, 0),
            min_inclusive=True,
        )
        self.assertFalse(r1.overlaps(r2))

    def test_overlaps_unbounded(self):
        """Unbounded ranges assume possible overlap."""
        r1 = VersionRange(min_version=SemVer(0, 8, 0), max_version=None)
        r2 = VersionRange(min_version=SemVer(0, 9, 0), max_version=SemVer(0, 10, 0))
        self.assertTrue(r1.overlaps(r2))


class TestParsePragma(unittest.TestCase):
    """Tests for parse_pragma function."""

    def test_parse_caret(self):
        """Parse caret version constraint."""
        r = parse_pragma("^0.8.0")
        self.assertIsNotNone(r)
        self.assertEqual(r.min_version, SemVer(0, 8, 0))
        self.assertEqual(r.max_version, SemVer(0, 9, 0))
        self.assertTrue(r.min_inclusive)
        self.assertFalse(r.max_inclusive)

    def test_parse_caret_with_patch(self):
        """Parse caret with full version."""
        r = parse_pragma("^0.8.20")
        self.assertIsNotNone(r)
        self.assertEqual(r.min_version, SemVer(0, 8, 20))
        self.assertEqual(r.max_version, SemVer(0, 9, 0))

    def test_parse_range(self):
        """Parse range constraint."""
        r = parse_pragma(">=0.8.0 <0.9.0")
        self.assertIsNotNone(r)
        self.assertEqual(r.min_version, SemVer(0, 8, 0))
        self.assertEqual(r.max_version, SemVer(0, 9, 0))
        self.assertTrue(r.min_inclusive)
        self.assertFalse(r.max_inclusive)

    def test_parse_range_inclusive(self):
        """Parse range with inclusive max."""
        r = parse_pragma(">=0.8.0 <=0.9.0")
        self.assertIsNotNone(r)
        self.assertTrue(r.min_inclusive)
        self.assertTrue(r.max_inclusive)

    def test_parse_gte_only(self):
        """Parse >= constraint only."""
        r = parse_pragma(">=0.8.0")
        self.assertIsNotNone(r)
        self.assertEqual(r.min_version, SemVer(0, 8, 0))
        self.assertIsNone(r.max_version)
        self.assertTrue(r.min_inclusive)

    def test_parse_lt_only(self):
        """Parse < constraint only."""
        r = parse_pragma("<0.9.0")
        self.assertIsNotNone(r)
        self.assertIsNone(r.min_version)
        self.assertEqual(r.max_version, SemVer(0, 9, 0))
        self.assertFalse(r.max_inclusive)

    def test_parse_exact_version(self):
        """Parse exact version."""
        r = parse_pragma("0.8.20")
        self.assertIsNotNone(r)
        self.assertEqual(r.min_version, SemVer(0, 8, 20))
        self.assertEqual(r.max_version, SemVer(0, 8, 20))
        self.assertTrue(r.min_inclusive)
        self.assertTrue(r.max_inclusive)

    def test_parse_invalid(self):
        """Return None for unparseable pragma."""
        self.assertIsNone(parse_pragma("invalid"))
        self.assertIsNone(parse_pragma(""))
        self.assertIsNone(parse_pragma("~0.8.0"))  # Not supported


class TestCheckPragmaCompatibility(unittest.TestCase):
    """Tests for check_pragma_compatibility function."""

    def test_compatible_same_caret(self):
        """Same caret versions are compatible."""
        result = check_pragma_compatibility("^0.8.0", "^0.8.0")
        self.assertEqual(result.status, CompatibilityStatus.COMPATIBLE)

    def test_compatible_overlapping(self):
        """Overlapping ranges are compatible."""
        result = check_pragma_compatibility("^0.8.0", ">=0.8.10 <0.9.0")
        self.assertEqual(result.status, CompatibilityStatus.COMPATIBLE)

    def test_incompatible_ranges(self):
        """Non-overlapping ranges are incompatible."""
        result = check_pragma_compatibility("^0.7.0", "^0.8.0")
        self.assertEqual(result.status, CompatibilityStatus.INCOMPATIBLE)
        self.assertIsNotNone(result.suggestion)

    def test_missing_test_pragma(self):
        """Missing test pragma returns MISSING."""
        result = check_pragma_compatibility(None, "^0.8.0")
        self.assertEqual(result.status, CompatibilityStatus.MISSING)
        self.assertIn("test file", result.message.lower())

    def test_missing_contract_pragma(self):
        """Missing contract pragma returns MISSING."""
        result = check_pragma_compatibility("^0.8.0", None)
        self.assertEqual(result.status, CompatibilityStatus.MISSING)
        self.assertIn("contract", result.message.lower())

    def test_missing_both(self):
        """Both missing returns MISSING with suggestion."""
        result = check_pragma_compatibility(None, None)
        self.assertEqual(result.status, CompatibilityStatus.MISSING)
        self.assertIsNotNone(result.suggestion)

    def test_unknown_for_unparseable(self):
        """Unparseable pragma returns UNKNOWN."""
        result = check_pragma_compatibility("~0.8.0", "^0.8.0")
        self.assertEqual(result.status, CompatibilityStatus.UNKNOWN)


class TestSuggestTestPragma(unittest.TestCase):
    """Tests for suggest_test_pragma function."""

    def test_suggest_from_caret(self):
        """Caret pragma is preserved."""
        suggestion = suggest_test_pragma("^0.8.20")
        self.assertEqual(suggestion, "^0.8.20")

    def test_suggest_from_range(self):
        """Range pragma is preserved."""
        suggestion = suggest_test_pragma(">=0.8.0 <0.9.0")
        self.assertEqual(suggestion, ">=0.8.0 <0.9.0")

    def test_suggest_from_exact(self):
        """Exact version gets caret added."""
        suggestion = suggest_test_pragma("0.8.20")
        self.assertEqual(suggestion, "^0.8.0")

    def test_suggest_default_for_none(self):
        """Default suggestion for missing pragma."""
        suggestion = suggest_test_pragma(None)
        self.assertEqual(suggestion, "^0.8.20")

    def test_suggest_from_gte(self):
        """Greater-than-or-equal preserved."""
        suggestion = suggest_test_pragma(">=0.8.0")
        self.assertEqual(suggestion, ">=0.8.0")


class TestGetPragmaFromFile(unittest.TestCase):
    """Tests for get_pragma_from_file function."""

    def test_extract_from_file(self):
        """Extract pragma from Solidity file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            sol_file = Path(tmpdir) / "Test.sol"
            sol_file.write_text(
                "// SPDX-License-Identifier: MIT\n"
                "pragma solidity ^0.8.20;\n"
                "contract Test {}\n"
            )
            pragma = get_pragma_from_file(sol_file)
            self.assertEqual(pragma, "^0.8.20")

    def test_returns_none_for_missing_file(self):
        """Return None for non-existent file."""
        pragma = get_pragma_from_file(Path("/nonexistent/file.sol"))
        self.assertIsNone(pragma)

    def test_returns_none_for_no_pragma(self):
        """Return None when file has no pragma."""
        with tempfile.TemporaryDirectory() as tmpdir:
            sol_file = Path(tmpdir) / "NoPragma.sol"
            sol_file.write_text("contract Test {}\n")
            pragma = get_pragma_from_file(sol_file)
            self.assertIsNone(pragma)


class TestFindCommonPragma(unittest.TestCase):
    """Tests for find_common_pragma function."""

    def test_single_pragma(self):
        """Single pragma returns itself."""
        result = find_common_pragma(["^0.8.0"])
        self.assertEqual(result, "^0.8.0")

    def test_empty_list(self):
        """Empty list returns None."""
        result = find_common_pragma([])
        self.assertIsNone(result)

    def test_overlapping_pragmas(self):
        """Overlapping pragmas return intersection."""
        result = find_common_pragma(["^0.8.0", ">=0.8.10 <0.9.0"])
        self.assertIsNotNone(result)
        # Result should be at least >=0.8.10 and <0.9.0
        self.assertIn("0.8.10", result)

    def test_non_overlapping_pragmas(self):
        """Non-overlapping pragmas return None."""
        result = find_common_pragma(["^0.7.0", "^0.8.0"])
        self.assertIsNone(result)

    def test_multiple_overlapping(self):
        """Multiple overlapping pragmas find common ground."""
        result = find_common_pragma([
            ">=0.8.0 <0.9.0",
            ">=0.8.5 <0.8.25",
            ">=0.8.10 <0.8.20",
        ])
        self.assertIsNotNone(result)
        # Should be [0.8.10, 0.8.20)
        self.assertIn("0.8.10", result)
        self.assertIn("0.8.20", result)


class TestCompatibilityResult(unittest.TestCase):
    """Tests for CompatibilityResult dataclass."""

    def test_result_attributes(self):
        """CompatibilityResult has all required attributes."""
        result = CompatibilityResult(
            status=CompatibilityStatus.COMPATIBLE,
            test_pragma="^0.8.0",
            contract_pragma="^0.8.0",
            message="Compatible",
            suggestion=None,
        )
        self.assertEqual(result.status, CompatibilityStatus.COMPATIBLE)
        self.assertEqual(result.test_pragma, "^0.8.0")
        self.assertEqual(result.contract_pragma, "^0.8.0")
        self.assertEqual(result.message, "Compatible")
        self.assertIsNone(result.suggestion)


class TestEdgeCases(unittest.TestCase):
    """Tests for edge cases and boundary conditions."""

    def test_whitespace_handling(self):
        """Pragma parsing handles whitespace."""
        r = parse_pragma("  ^0.8.0  ")
        self.assertIsNotNone(r)
        self.assertEqual(r.min_version, SemVer(0, 8, 0))

    def test_version_with_leading_v(self):
        """Version parsing handles leading 'v'."""
        v = SemVer.parse("v0.8.20")
        self.assertIsNotNone(v)
        self.assertEqual(v.major, 0)
        self.assertEqual(v.minor, 8)
        self.assertEqual(v.patch, 20)

    def test_large_version_numbers(self):
        """Handle large version numbers."""
        v = SemVer.parse("999.999.999")
        self.assertIsNotNone(v)
        self.assertEqual(v.major, 999)

    def test_zero_version(self):
        """Handle 0.0.0 version."""
        v = SemVer.parse("0.0.0")
        self.assertIsNotNone(v)
        self.assertEqual(v.major, 0)
        self.assertEqual(v.minor, 0)
        self.assertEqual(v.patch, 0)


if __name__ == "__main__":
    unittest.main()
