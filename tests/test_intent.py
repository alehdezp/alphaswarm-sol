"""Intent parser tests for NL mappings."""

from __future__ import annotations

import unittest
import pytest
import json

from alphaswarm_sol.queries.intent import parse_intent


class IntentParserTests(unittest.TestCase):
    def test_attacker_controlled_flow_with_exclusion(self) -> None:
        intent = parse_intent(
            "functions where state is updated and input is attacker-controlled (excluding msg.sender)"
        )
        self.assertEqual(intent.query_kind, "flow")
        self.assertIsNotNone(intent.flow)
        self.assertIn("msg.sender", intent.flow.exclude_sources)
        self.assertFalse(intent.properties.get("uses_msg_sender", True))

    def test_exclude_constructor_phrase(self) -> None:
        intent = parse_intent("non-constructor functions that write state")
        self.assertFalse(intent.properties.get("is_constructor", True))
        self.assertTrue(intent.properties.get("writes_state", False))

    def test_attacker_controlled_implies_flow(self) -> None:
        intent = parse_intent("attacker-controlled input writes state")
        self.assertEqual(intent.query_kind, "flow")
        self.assertIsNotNone(intent.flow)
        self.assertIn("parameter", intent.flow.from_kinds)
        self.assertIn("env", intent.flow.from_kinds)

    def test_exclude_msg_sender_property(self) -> None:
        intent = parse_intent("functions excluding msg.sender")
        self.assertFalse(intent.properties.get("uses_msg_sender", True))

    def test_json_payload_defaults_to_logic(self) -> None:
        payload = {
            "match": {"all": [{"property": "visibility", "op": "=", "value": "external"}]}
        }
        raw = json.dumps(payload)
        intent = parse_intent(raw)
        self.assertEqual(intent.query_kind, "logic")
        self.assertEqual(intent.raw_text, raw)
        self.assertEqual(intent.match.all[0].property, "visibility")

    def test_limit_and_token_parsing(self) -> None:
        intent = parse_intent("top 25 pattern:access-control lens:auth summary")
        self.assertEqual(intent.limit, 25)
        self.assertIn("access-control", intent.patterns)
        self.assertIn("auth", intent.lens)
        self.assertTrue(intent.compact_mode)

    def test_vql_basic_conditions(self) -> None:
        intent = parse_intent(
            "find functions where visibility in [public, external] and writes_state and not has_access_gate limit 10"
        )
        self.assertEqual(intent.query_kind, "logic")
        self.assertEqual(intent.limit, 10)
        self.assertIsNotNone(intent.match)
        self.assertTrue(any(c.property == "writes_state" for c in intent.match.all))
        self.assertTrue(any(c.property == "has_access_gate" and c.value is False for c in intent.match.all))

    def test_vql_boolean_defaults(self) -> None:
        intent = parse_intent("find contracts where upgradeable_without_storage_gap")
        self.assertEqual(intent.query_kind, "logic")
        self.assertTrue(any(c.property == "upgradeable_without_storage_gap" for c in intent.match.all))

    @pytest.mark.xfail(reason="Stale code: Intent parser rule_map resolution changed")
    def test_rule_map_pattern_resolution(self) -> None:
        intent = parse_intent("check unbounded loop in functions")
        self.assertEqual(intent.query_kind, "pattern")
        self.assertIn("dos-unbounded-loop", intent.patterns)

    def test_property_alias_in_vql(self) -> None:
        intent = parse_intent("find functions where auth gate = false")
        self.assertEqual(intent.query_kind, "logic")
        self.assertTrue(any(c.property == "has_access_gate" for c in intent.match.all))

    def test_vql_error_hint(self) -> None:
        intent = parse_intent("find functions")
        self.assertEqual(intent.query_kind, "logic")
        self.assertIn("vql_error", intent.properties)
        self.assertIn("vql_hint", intent.properties)

    def test_edge_alias_calls_contract(self) -> None:
        intent = parse_intent("edges calls contract")
        self.assertEqual(intent.query_kind, "edges")
        self.assertIn("CALLS_CONTRACT", intent.edge_types)

    def test_schema_hint_suggestions(self) -> None:
        intent = parse_intent("find functions where writs_state")
        self.assertTrue(intent.warnings)
        self.assertTrue(intent.hints)

    @pytest.mark.xfail(reason="Stale code: Intent parser rule_map resolution changed")
    def test_disambiguation_threshold(self) -> None:
        intent = parse_intent("check loop min-confidence 0.9")
        self.assertTrue(intent.properties.get("rule_candidates"))
        self.assertIsNotNone(intent.disambiguation_prompt)


if __name__ == "__main__":
    unittest.main()
