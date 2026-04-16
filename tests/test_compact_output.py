"""Tests for compact output format.

Task 9.3/9.8: Tests for token-optimized serialization.
"""

import json
import unittest

import yaml

from alphaswarm_sol.output import (
    KEY_ABBREVIATIONS,
    KEY_EXPANSIONS,
    VALUE_ABBREVIATIONS,
    CompactDecoder,
    CompactEncoder,
    DetailLevel,
    abbreviate_keys,
    abbreviate_value,
    compare_token_counts,
    decode_finding,
    encode_finding,
    expand_keys,
    expand_value,
    format_context,
    get_abbreviation,
    get_expansion,
)


class TestAbbreviations(unittest.TestCase):
    """Test key and value abbreviations."""

    def test_key_abbreviations_defined(self):
        """Key abbreviations are defined."""
        self.assertIn("finding_id", KEY_ABBREVIATIONS)
        self.assertIn("severity", KEY_ABBREVIATIONS)
        self.assertEqual(KEY_ABBREVIATIONS["finding_id"], "fid")
        self.assertEqual(KEY_ABBREVIATIONS["severity"], "sev")

    def test_key_expansions_inverse(self):
        """Key expansions are inverse of abbreviations."""
        for full, abbr in KEY_ABBREVIATIONS.items():
            self.assertEqual(KEY_EXPANSIONS[abbr], full)

    def test_value_abbreviations_defined(self):
        """Value abbreviations are defined."""
        self.assertIn("critical", VALUE_ABBREVIATIONS)
        self.assertEqual(VALUE_ABBREVIATIONS["critical"], "CRIT")

    def test_abbreviate_keys_dict(self):
        """abbreviate_keys works on dictionaries."""
        data = {"finding_id": "VKG-001", "severity": "critical"}
        result = abbreviate_keys(data)

        self.assertIn("fid", result)
        self.assertIn("sev", result)
        self.assertNotIn("finding_id", result)

    def test_abbreviate_keys_nested(self):
        """abbreviate_keys handles nested structures."""
        data = {
            "finding_id": "VKG-001",
            "evidence": [{"line_number": 42}],
        }
        result = abbreviate_keys(data)

        self.assertEqual(result["fid"], "VKG-001")
        self.assertEqual(result["ev"][0]["ln"], 42)

    def test_abbreviate_keys_values(self):
        """abbreviate_keys abbreviates string values."""
        data = {"severity": "critical"}
        result = abbreviate_keys(data)

        self.assertEqual(result["sev"], "CRIT")

    def test_expand_keys_dict(self):
        """expand_keys expands abbreviated keys."""
        data = {"fid": "VKG-001", "sev": "CRIT"}
        result = expand_keys(data)

        self.assertIn("finding_id", result)
        self.assertIn("severity", result)
        self.assertEqual(result["severity"], "critical")

    def test_expand_keys_nested(self):
        """expand_keys handles nested structures."""
        data = {"fid": "VKG-001", "ev": [{"ln": 42}]}
        result = expand_keys(data)

        self.assertEqual(result["finding_id"], "VKG-001")
        self.assertEqual(result["evidence"][0]["line_number"], 42)

    def test_abbreviate_value(self):
        """abbreviate_value works on single values."""
        self.assertEqual(abbreviate_value("critical"), "CRIT")
        self.assertEqual(abbreviate_value("unknown"), "unknown")

    def test_expand_value(self):
        """expand_value works on single values."""
        self.assertEqual(expand_value("CRIT"), "critical")
        self.assertEqual(expand_value("unknown"), "unknown")

    def test_get_abbreviation(self):
        """get_abbreviation returns abbreviation."""
        self.assertEqual(get_abbreviation("finding_id"), "fid")
        self.assertEqual(get_abbreviation("unknown"), "unknown")

    def test_get_expansion(self):
        """get_expansion returns full name."""
        self.assertEqual(get_expansion("fid"), "finding_id")
        self.assertEqual(get_expansion("unknown"), "unknown")


class TestCompactEncoder(unittest.TestCase):
    """Test CompactEncoder class."""

    def _sample_finding(self):
        """Create sample finding for tests."""
        return {
            "finding_id": "VKG-001",
            "pattern_id": "vm-001",
            "severity": "critical",
            "confidence": 0.95,
            "contract": "Test",
            "function": "withdraw",
            "line_number": 42,
            "description": "Reentrancy vulnerability",
        }

    def test_encode_produces_yaml(self):
        """Encoder produces valid YAML."""
        finding = self._sample_finding()
        encoder = CompactEncoder()
        compact = encoder.encode(finding)

        # Should be valid YAML
        parsed = yaml.safe_load(compact)
        self.assertIsNotNone(parsed)

    def test_keys_abbreviated(self):
        """Keys are abbreviated in output."""
        finding = self._sample_finding()
        encoder = CompactEncoder()
        compact = encoder.encode(finding)

        self.assertIn("fid:", compact)  # finding_id -> fid
        self.assertIn("sev:", compact)  # severity -> sev
        self.assertNotIn("finding_id:", compact)

    def test_values_abbreviated(self):
        """Values are abbreviated in output."""
        finding = self._sample_finding()
        encoder = CompactEncoder()
        compact = encoder.encode(finding)

        self.assertIn("CRIT", compact)  # critical -> CRIT

    def test_detail_level_default(self):
        """Default detail level is DETAILED."""
        encoder = CompactEncoder()
        self.assertEqual(encoder.detail, DetailLevel.DETAILED)

    def test_encode_json(self):
        """encode_json produces valid JSON."""
        finding = self._sample_finding()
        encoder = CompactEncoder()
        compact = encoder.encode_json(finding)

        # Should be valid JSON
        parsed = json.loads(compact)
        self.assertIn("fid", parsed)


class TestCompactDecoder(unittest.TestCase):
    """Test CompactDecoder class."""

    def test_decode_yaml(self):
        """Decoder decodes YAML and expands keys."""
        yaml_str = "fid: VKG-001\nsev: CRIT\n"
        decoder = CompactDecoder()
        result = decoder.decode(yaml_str)

        self.assertEqual(result["finding_id"], "VKG-001")
        self.assertEqual(result["severity"], "critical")

    def test_decode_empty(self):
        """Decoder handles empty input."""
        decoder = CompactDecoder()
        result = decoder.decode("")

        self.assertEqual(result, {})

    def test_decode_json(self):
        """decode_json decodes JSON and expands keys."""
        json_str = '{"fid":"VKG-001","sev":"CRIT"}'
        decoder = CompactDecoder()
        result = decoder.decode_json(json_str)

        self.assertEqual(result["finding_id"], "VKG-001")


class TestRoundTrip(unittest.TestCase):
    """Test encode/decode round trips."""

    def _sample_finding(self):
        """Create sample finding for tests."""
        return {
            "finding_id": "VKG-001",
            "pattern_id": "vm-001",
            "severity": "critical",
            "confidence": 0.95,
            "contract": "Test",
            "function": "withdraw",
            "line_number": 42,
        }

    def test_round_trip_yaml(self):
        """Encode then decode preserves data."""
        finding = self._sample_finding()
        encoder = CompactEncoder()
        decoder = CompactDecoder()

        compact = encoder.encode(finding)
        recovered = decoder.decode(compact)

        self.assertEqual(recovered["finding_id"], finding["finding_id"])
        self.assertEqual(recovered["severity"], finding["severity"])

    def test_round_trip_json(self):
        """JSON encode then decode preserves data."""
        finding = self._sample_finding()
        encoder = CompactEncoder()
        decoder = CompactDecoder()

        compact = encoder.encode_json(finding)
        recovered = decoder.decode_json(compact)

        self.assertEqual(recovered["finding_id"], finding["finding_id"])


class TestDetailLevels(unittest.TestCase):
    """Test detail level filtering."""

    def test_detail_level_values(self):
        """DetailLevel enum has expected values."""
        self.assertEqual(DetailLevel.SUMMARY.value, "summary")
        self.assertEqual(DetailLevel.DETAILED.value, "detailed")
        self.assertEqual(DetailLevel.FULL.value, "full")

    def test_full_includes_everything(self):
        """Full level includes all fields."""
        data = {
            "finding_id": "VKG-001",
            "raw_source": "long source code...",
            "debug_info": "verbose debug...",
        }

        encoder = CompactEncoder(detail=DetailLevel.FULL)
        compact = encoder.encode(data)
        parsed = yaml.safe_load(compact)

        # All fields present (with abbreviated keys)
        self.assertIn("raw_source", parsed)
        self.assertIn("debug_info", parsed)

    def test_detailed_excludes_verbose(self):
        """Detailed level excludes verbose fields."""
        data = {
            "finding_id": "VKG-001",
            "raw_source": "long source code...",
            "description": "Short description",
        }

        encoder = CompactEncoder(detail=DetailLevel.DETAILED)
        compact = encoder.encode(data)
        parsed = yaml.safe_load(compact)

        # Verbose field excluded
        self.assertNotIn("raw_source", parsed)
        # Non-verbose fields included
        self.assertIn("desc", parsed)

    def test_summary_includes_minimal(self):
        """Summary level includes only key fields."""
        data = {
            "finding_id": "VKG-001",
            "severity": "critical",
            "description": "Long description",
            "recommendation": "Fix this",
        }

        encoder = CompactEncoder(detail=DetailLevel.SUMMARY)
        compact = encoder.encode(data)
        parsed = yaml.safe_load(compact)

        # Summary fields included
        self.assertIn("fid", parsed)
        self.assertIn("sev", parsed)
        # Non-summary fields excluded
        self.assertNotIn("desc", parsed)
        self.assertNotIn("rec", parsed)


class TestTokenReduction(unittest.TestCase):
    """Test token reduction calculations."""

    def _sample_finding(self):
        """Create sample finding for tests."""
        return {
            "finding_id": "VKG-001",
            "pattern_id": "reentrancy-classic",
            "severity": "critical",
            "confidence": 0.95,
            "contract": "Vault",
            "function": "withdraw",
            "line_number": 42,
            "description": "State update after external call allows reentrancy",
            "evidence": [
                {"type": "external_call", "line": 40, "target": "msg.sender.call"},
                {"type": "state_write", "line": 45, "variable": "balances"},
            ],
            "recommendation": "Move state update before external call (CEI pattern)",
        }

    def test_compare_token_counts(self):
        """compare_token_counts returns expected keys."""
        finding = self._sample_finding()
        result = compare_token_counts(finding)

        self.assertIn("json_pretty_chars", result)
        self.assertIn("compact_chars", result)
        self.assertIn("reduction_percent", result)

    def test_compact_smaller_than_json(self):
        """Compact format uses fewer characters."""
        finding = self._sample_finding()
        result = compare_token_counts(finding)

        self.assertLess(result["compact_chars"], result["json_pretty_chars"])

    def test_reduction_at_least_25_percent(self):
        """Compact format achieves at least 25% reduction."""
        finding = self._sample_finding()
        result = compare_token_counts(finding)

        self.assertGreaterEqual(result["reduction_percent"], 25)


class TestConvenienceFunctions(unittest.TestCase):
    """Test convenience functions."""

    def _sample_finding(self):
        """Create sample finding for tests."""
        return {
            "finding_id": "VKG-001",
            "severity": "critical",
        }

    def test_encode_finding(self):
        """encode_finding works."""
        finding = self._sample_finding()
        compact = encode_finding(finding)

        self.assertIn("fid:", compact)
        self.assertIn("sev:", compact)

    def test_decode_finding(self):
        """decode_finding works."""
        compact = "fid: VKG-001\nsev: CRIT\n"
        finding = decode_finding(compact)

        self.assertEqual(finding["finding_id"], "VKG-001")
        self.assertEqual(finding["severity"], "critical")

    def test_format_context_yaml(self):
        """format_context produces YAML."""
        data = {"finding_id": "VKG-001"}
        result = format_context(data, format_type="yaml")

        # Should be YAML format
        parsed = yaml.safe_load(result)
        self.assertIsNotNone(parsed)

    def test_format_context_json(self):
        """format_context produces JSON when requested."""
        data = {"finding_id": "VKG-001"}
        result = format_context(data, format_type="json")

        # Should be JSON format
        parsed = json.loads(result)
        self.assertIn("fid", parsed)


if __name__ == "__main__":
    unittest.main()
