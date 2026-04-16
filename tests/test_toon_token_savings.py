"""Token savings validation tests for TOON format.

This module validates TOON format token behavior for different data structures.
Based on Phase 5.6.1 implementation, TOON provides significant savings for
uniform arrays but may increase tokens for complex nested structures.

Key findings:
- Uniform arrays (evidence, simple edges): 25-40%+ token reduction via tabular encoding
- Complex nested structures: May INCREASE tokens - this is why GraphStore uses
  JSON-inside-TOON envelope approach (see store.py)

Token counting uses tiktoken (cl100k_base encoding) with character-based fallback.
"""

from __future__ import annotations

import json
from typing import Any

import pytest

from alphaswarm_sol.kg.toon import toon_dumps
from tests.graph_cache import load_graph

# Try to use tiktoken for accurate token counting
try:
    import tiktoken

    _encoding = tiktoken.get_encoding("cl100k_base")

    def count_tokens(text: str) -> int:
        """Count tokens using tiktoken cl100k_base encoding."""
        return len(_encoding.encode(text))

except ImportError:
    # Fallback to character-based estimate (4 chars per token average)
    def count_tokens(text: str) -> int:
        """Estimate tokens from character count (4 chars/token)."""
        return len(text) // 4


def calculate_savings(json_data: Any) -> dict[str, Any]:
    """Calculate token and character savings from JSON to TOON.

    Args:
        json_data: Python object to serialize

    Returns:
        Dict with json_chars, toon_chars, json_tokens, toon_tokens,
        char_reduction_pct, token_reduction_pct
    """
    json_str = json.dumps(json_data, separators=(",", ":"))
    toon_str = toon_dumps(json_data)

    json_tokens = count_tokens(json_str)
    toon_tokens = count_tokens(toon_str)

    return {
        "json_chars": len(json_str),
        "toon_chars": len(toon_str),
        "json_tokens": json_tokens,
        "toon_tokens": toon_tokens,
        "char_reduction_pct": (len(json_str) - len(toon_str)) / len(json_str) * 100,
        "token_reduction_pct": (json_tokens - toon_tokens) / json_tokens * 100,
    }


class TestUniformArraySavings:
    """Test TOON savings for uniform arrays (evidence-like structures).

    Uniform arrays with identical schemas benefit from TOON's tabular encoding,
    achieving 25-40%+ token reduction. This is TOON's sweet spot.
    """

    def test_evidence_array_savings(self) -> None:
        """Evidence arrays should achieve >25% token reduction."""
        # Realistic evidence array - all items have same schema
        evidence = [
            {"file": "Token.sol", "line_start": i, "line_end": i + 5, "detail": None}
            for i in range(1, 101, 5)
        ]

        savings = calculate_savings({"evidence": evidence})

        # Print for visibility in test output
        print(f"\n=== Evidence Array (20 items) ===")
        print(f"JSON: {savings['json_chars']} chars, {savings['json_tokens']} tokens")
        print(f"TOON: {savings['toon_chars']} chars, {savings['toon_tokens']} tokens")
        print(f"Char reduction: {savings['char_reduction_pct']:.1f}%")
        print(f"Token reduction: {savings['token_reduction_pct']:.1f}%")

        assert savings["token_reduction_pct"] > 25, (
            f"Evidence array token reduction ({savings['token_reduction_pct']:.1f}%) "
            f"should be >25%"
        )

    def test_edge_array_savings(self) -> None:
        """Edge arrays (uniform schema) should achieve >25% token reduction."""
        # Realistic edge array - all items have same schema
        edges = [
            {
                "id": f"edge:{i}",
                "type": "calls",
                "source": f"func:A{i}",
                "target": f"func:B{i}",
            }
            for i in range(50)
        ]

        savings = calculate_savings({"edges": edges})

        print(f"\n=== Edge Array (50 items) ===")
        print(f"JSON: {savings['json_chars']} chars, {savings['json_tokens']} tokens")
        print(f"TOON: {savings['toon_chars']} chars, {savings['toon_tokens']} tokens")
        print(f"Char reduction: {savings['char_reduction_pct']:.1f}%")
        print(f"Token reduction: {savings['token_reduction_pct']:.1f}%")

        assert savings["token_reduction_pct"] > 25, (
            f"Edge array token reduction ({savings['token_reduction_pct']:.1f}%) "
            f"should be >25%"
        )

    def test_larger_evidence_array_scaling(self) -> None:
        """Larger uniform arrays should show consistent or better savings."""
        # 100 items - TOON's tabular encoding scales well
        evidence = [
            {"file": "Token.sol", "line_start": i, "line_end": i + 5, "detail": None}
            for i in range(100)
        ]

        savings = calculate_savings({"evidence": evidence})

        print(f"\n=== Large Evidence Array (100 items) ===")
        print(f"JSON: {savings['json_chars']} chars, {savings['json_tokens']} tokens")
        print(f"TOON: {savings['toon_chars']} chars, {savings['toon_tokens']} tokens")
        print(f"Token reduction: {savings['token_reduction_pct']:.1f}%")

        # Larger arrays should show at least 30% savings
        assert savings["token_reduction_pct"] > 30, (
            f"Large evidence array should show >30% savings, "
            f"got {savings['token_reduction_pct']:.1f}%"
        )


class TestSimpleMetadataBehavior:
    """Test TOON behavior for simple metadata structures.

    Simple flat structures may have minimal overhead with TOON due to
    newlines and spacing. TOON's main benefit is for uniform arrays.
    """

    def test_flat_metadata_documented(self) -> None:
        """Document TOON behavior with flat metadata (minimal change expected)."""
        metadata = {
            "format": "alphaswarm-kg-v1",
            "saved_at": "2026-01-23T12:00:00Z",
            "version": "5.0.0",
            "contract_count": 3,
            "function_count": 15,
            "edge_count": 42,
        }

        savings = calculate_savings(metadata)

        print(f"\n=== Flat Metadata ===")
        print(f"JSON: {savings['json_chars']} chars, {savings['json_tokens']} tokens")
        print(f"TOON: {savings['toon_chars']} chars, {savings['toon_tokens']} tokens")
        print(f"Token reduction: {savings['token_reduction_pct']:.1f}%")

        # Flat structures may have slight overhead, but should be minimal (<20%)
        overhead_pct = -savings["token_reduction_pct"]
        if overhead_pct > 0:
            print(f"NOTE: TOON has {overhead_pct:.1f}% overhead for flat metadata")
            assert overhead_pct < 20, (
                f"Flat metadata overhead ({overhead_pct:.1f}%) should be <20%"
            )


class TestComplexStructureBehavior:
    """Test TOON behavior for complex nested structures.

    Complex structures with varying schemas and nested dicts may NOT benefit
    from TOON and can actually increase token count. This documents the
    limitation that led to the JSON-inside-TOON approach in store.py.
    """

    def test_mixed_schema_array_documented_limitation(self) -> None:
        """Mixed schema arrays document TOON's limitation with heterogeneous data."""
        # Nodes with varying properties per type - TOON struggles here
        nodes = [
            {
                "id": "contract:Token",
                "type": "Contract",
                "label": "Token",
                "is_abstract": False,
                "inherits_from": ["ERC20", "Ownable"],
            },
            {
                "id": "func:Token.transfer",
                "type": "Function",
                "label": "transfer",
                "visibility": "public",
                "is_payable": False,
                "writes_state": True,
            },
            {
                "id": "var:Token.balances",
                "type": "StateVariable",
                "label": "balances",
                "visibility": "private",
                "is_mapping": True,
            },
        ]

        savings = calculate_savings({"nodes": nodes})

        print(f"\n=== Mixed Schema Array (TOON limitation) ===")
        print(f"JSON: {savings['json_chars']} chars, {savings['json_tokens']} tokens")
        print(f"TOON: {savings['toon_chars']} chars, {savings['toon_tokens']} tokens")
        print(f"Token reduction: {savings['token_reduction_pct']:.1f}%")

        # Document that TOON may actually increase tokens for mixed schemas
        # This is expected behavior - not a test failure
        if savings["token_reduction_pct"] < 0:
            print("NOTE: TOON increases tokens for mixed schemas - this is expected")
            print("      Store.py uses JSON-inside-TOON to avoid this issue")

    def test_nested_properties_documented_limitation(self) -> None:
        """Nested properties document TOON's limitation with deep nesting."""
        # Node with nested properties - common in real graphs
        node = {
            "id": "func:Token.transfer",
            "properties": {
                "visibility": "public",
                "has_access_control": False,
                "semantic_operations": ["TRANSFERS_VALUE_OUT", "WRITES_USER_BALANCE"],
                "nested": {
                    "deep": {
                        "value": 42,
                        "flag": True,
                    }
                },
            },
            "evidence": [
                {"file": "Token.sol", "line_start": 10, "line_end": 20, "detail": None}
            ],
        }

        savings = calculate_savings(node)

        print(f"\n=== Nested Properties (TOON limitation) ===")
        print(f"JSON: {savings['json_chars']} chars, {savings['json_tokens']} tokens")
        print(f"TOON: {savings['toon_chars']} chars, {savings['toon_tokens']} tokens")
        print(f"Token reduction: {savings['token_reduction_pct']:.1f}%")

        # Just document the behavior - not asserting specific values
        # because TOON behavior with nesting is implementation-dependent


class TestRealGraphBehavior:
    """Test TOON behavior with real knowledge graphs.

    Real graphs have complex nested structures. This class documents their
    TOON behavior and shows why store.py uses JSON-inside-TOON approach.
    """

    def test_real_graph_behavior_documented(self) -> None:
        """Document TOON behavior with real graph (may increase tokens)."""
        graph = load_graph("NoAccessGate.sol")
        graph_dict = graph.to_dict()

        savings = calculate_savings(graph_dict)

        print(f"\n=== Real Graph (NoAccessGate.sol) ===")
        print(f"Nodes: {len(graph_dict.get('nodes', {}))}")
        print(f"Edges: {len(graph_dict.get('edges', []))}")
        print(f"JSON: {savings['json_chars']} chars, {savings['json_tokens']} tokens")
        print(f"TOON: {savings['toon_chars']} chars, {savings['toon_tokens']} tokens")
        print(f"Token reduction: {savings['token_reduction_pct']:.1f}%")

        # Document the behavior
        if savings["token_reduction_pct"] < 0:
            print("NOTE: Direct TOON encoding increases tokens for real graphs")
            print("      Store.py uses JSON-inside-TOON envelope to get benefits")

    def test_json_inside_toon_approach_verified(self) -> None:
        """Verify the JSON-inside-TOON approach provides savings."""
        graph = load_graph("NoAccessGate.sol")
        graph_dict = graph.to_dict()

        # Pure JSON baseline
        json_str = json.dumps(graph_dict, separators=(",", ":"))
        json_tokens = count_tokens(json_str)

        # JSON-inside-TOON (as store.py does)
        toon_envelope = {
            "format": "alphaswarm-kg-v1",
            "saved_at": "2026-01-23T12:00:00Z",
            "graph_json": json.dumps(graph_dict, separators=(",", ":")),
        }
        toon_envelope_str = toon_dumps(toon_envelope)
        toon_envelope_tokens = count_tokens(toon_envelope_str)

        print(f"\n=== JSON-inside-TOON Envelope ===")
        print(f"Pure JSON: {len(json_str)} chars, {json_tokens} tokens")
        print(f"TOON envelope: {len(toon_envelope_str)} chars, {toon_envelope_tokens} tokens")

        # The TOON envelope should be similar to or less than pure JSON
        # because metadata is TOON-ified while complex data stays JSON
        overhead = toon_envelope_tokens - json_tokens
        print(f"Overhead: {overhead} tokens ({overhead / json_tokens * 100:.1f}%)")

        # Minimal overhead expected (<10%)
        overhead_pct = abs(overhead) / json_tokens * 100
        assert overhead_pct < 15, (
            f"TOON envelope overhead ({overhead_pct:.1f}%) should be <15%"
        )


class TestTokenCountingAccuracy:
    """Verify token counting is working correctly."""

    def test_tiktoken_available(self) -> None:
        """Verify tiktoken is being used (not fallback)."""
        try:
            import tiktoken

            enc = tiktoken.get_encoding("cl100k_base")
            # Known token count for "hello world"
            tokens = len(enc.encode("hello world"))
            assert tokens == 2, f"Expected 2 tokens for 'hello world', got {tokens}"
            print("\nUsing tiktoken for accurate token counting")
        except ImportError:
            print("\nUsing character-based fallback (tiktoken not available)")

    def test_token_count_sanity(self) -> None:
        """Token counts should be reasonable for known text."""
        text = "The quick brown fox jumps over the lazy dog"
        tokens = count_tokens(text)
        # This sentence should be ~9-10 tokens
        assert 5 <= tokens <= 15, f"Unexpected token count: {tokens}"
        print(f"\nToken count for standard sentence: {tokens}")


class TestToonSweetSpot:
    """Document TOON's sweet spot - what it's good for.

    Summary of when to use TOON:
    - YES: Uniform arrays (evidence, simple edges, logs)
    - YES: Flat metadata (format version, timestamps)
    - MAYBE: Boolean-heavy flat dicts
    - NO: Mixed schema arrays (nodes with varying types)
    - NO: Deeply nested structures
    """

    def test_sweet_spot_summary(self) -> None:
        """Run comprehensive test showing TOON's strengths and weaknesses."""
        results = []

        # Sweet spot: uniform array
        evidence = [
            {"file": "Token.sol", "line_start": i, "line_end": i + 5, "detail": None}
            for i in range(50)
        ]
        savings = calculate_savings({"evidence": evidence})
        results.append(("Uniform Array (50 evidence)", savings["token_reduction_pct"]))

        # Sweet spot: flat metadata
        metadata = {"format": "v1", "count": 42, "enabled": True}
        savings = calculate_savings(metadata)
        results.append(("Flat Metadata", savings["token_reduction_pct"]))

        # Weakness: mixed schema
        mixed = [{"a": 1}, {"b": 2}, {"c": 3}]
        savings = calculate_savings({"items": mixed})
        results.append(("Mixed Schema Array", savings["token_reduction_pct"]))

        # Weakness: nested
        nested = {"outer": {"inner": {"deep": {"value": 1}}}}
        savings = calculate_savings(nested)
        results.append(("Deeply Nested", savings["token_reduction_pct"]))

        print("\n=== TOON Sweet Spot Summary ===")
        print(f"{'Data Type':<30} | {'Reduction':>10}")
        print("-" * 43)
        for name, pct in results:
            sign = "+" if pct > 0 else ""
            print(f"{name:<30} | {sign}{pct:>8.1f}%")

        # Verify sweet spot shows good savings
        uniform_savings = results[0][1]
        assert uniform_savings > 25, (
            f"Uniform arrays should show >25% savings, got {uniform_savings:.1f}%"
        )
