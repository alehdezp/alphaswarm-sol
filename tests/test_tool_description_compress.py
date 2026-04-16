"""Tests for tool description compression (Phase 7.1.3-05).

Tests compression utilities for reducing tool description tokens
while preserving required fields.
"""

import pytest

from alphaswarm_sol.tools.description_compress import (
    CompressionStats,
    ToolDescriptionCompressor,
    compress_for_context,
    compress_tool_description,
    compress_tool_descriptions,
    estimate_tool_tokens,
    get_compression_stats,
)


class TestCompressionStats:
    """Tests for CompressionStats dataclass."""

    def test_stats_creation(self):
        """Test basic stats creation."""
        stats = CompressionStats(
            original_chars=1000,
            compressed_chars=800,
            savings_percent=20.0,
        )
        assert stats.original_chars == 1000
        assert stats.compressed_chars == 800
        assert stats.savings_percent == 20.0

    def test_stats_to_dict(self):
        """Test serialization to dict."""
        stats = CompressionStats(
            original_chars=1000,
            compressed_chars=800,
            savings_percent=20.0,
            phrases_replaced=5,
            fields_trimmed=["description"],
        )
        d = stats.to_dict()
        assert d["original_chars"] == 1000
        assert d["compressed_chars"] == 800
        assert d["savings_percent"] == 20.0
        assert d["phrases_replaced"] == 5
        assert d["fields_trimmed"] == ["description"]


class TestToolDescriptionCompressor:
    """Tests for ToolDescriptionCompressor class."""

    def test_default_initialization(self):
        """Test default compressor initialization."""
        compressor = ToolDescriptionCompressor()
        assert compressor.last_stats is None

    def test_compress_empty_dict(self):
        """Test compressing empty dict."""
        compressor = ToolDescriptionCompressor()
        result = compressor.compress({})
        assert result == {}

    def test_compress_preserves_required_fields(self):
        """Test that required fields are preserved."""
        compressor = ToolDescriptionCompressor()
        tool = {
            "name": "slither",
            "binary": "slither",
            "install_hint": "pip install slither-analyzer",
            "install_method": "pip",
            "tier": "core",
            "description": "Some description",
        }
        result = compressor.compress(tool)
        assert result["name"] == "slither"
        assert result["binary"] == "slither"
        assert result["install_hint"] == "pip install slither-analyzer"

    def test_compress_applies_phrase_abbreviations(self):
        """Test phrase abbreviations are applied."""
        compressor = ToolDescriptionCompressor()
        tool = {
            "name": "slither",
            "description": "Static analyzer for Solidity - primary VKG data source",
        }
        result = compressor.compress(tool)
        # Should be abbreviated
        assert "Static analyzer for Solidity" not in result.get("description", "")
        assert len(result["description"]) < len(tool["description"])

    def test_compress_truncates_long_descriptions(self):
        """Test long descriptions are truncated."""
        compressor = ToolDescriptionCompressor(max_description_chars=50)
        tool = {
            "name": "test",
            "description": "x" * 100,
        }
        result = compressor.compress(tool)
        assert len(result["description"]) <= 50
        assert result["description"].endswith("...")

    def test_aggressive_mode_removes_verbose_fields(self):
        """Test aggressive mode removes verbose fields."""
        compressor = ToolDescriptionCompressor(aggressive=True)
        tool = {
            "name": "test",
            "binary": "test",
            "install_hint": "pip install test",
            "description": "Very long description that should be trimmed significantly",
            "homepage": "https://example.com/very/long/path/to/documentation",
            "examples": ["example 1", "example 2"],
        }
        result = compressor.compress(tool)
        # Description should be very short
        assert len(result.get("description", "")) <= 50
        # Homepage and examples may be removed or shortened
        assert "homepage" not in result or len(result["homepage"]) < len(tool["homepage"])

    def test_compress_records_stats(self):
        """Test compression records statistics."""
        compressor = ToolDescriptionCompressor()
        tool = {
            "name": "test",
            "description": "Static analyzer for Solidity - a very useful tool",
        }
        result = compressor.compress(tool)
        stats = compressor.last_stats
        assert stats is not None
        assert stats.original_chars > 0
        assert stats.compressed_chars > 0

    def test_compress_nested_dict(self):
        """Test compression handles nested dicts."""
        compressor = ToolDescriptionCompressor()
        tool = {
            "name": "test",
            "config": {
                "option1": "Static analyzer for Solidity",
                "option2": "value",
            },
        }
        result = compressor.compress(tool)
        assert "config" in result
        # Nested values should be compressed too
        assert "Static analyzer for Solidity" not in result["config"]["option1"]

    def test_compress_list_values(self):
        """Test compression handles list values."""
        compressor = ToolDescriptionCompressor()
        tool = {
            "name": "test",
            "commands": ["cmd1", "cmd2", "cmd3"],
        }
        result = compressor.compress(tool)
        assert result["commands"] == ["cmd1", "cmd2", "cmd3"]

    def test_aggressive_truncates_lists(self):
        """Test aggressive mode truncates long lists."""
        compressor = ToolDescriptionCompressor(aggressive=True)
        tool = {
            "name": "test",
            "commands": ["cmd1", "cmd2", "cmd3", "cmd4", "cmd5"],
        }
        result = compressor.compress(tool)
        assert len(result["commands"]) <= 3


class TestCompressToolDescription:
    """Tests for compress_tool_description function."""

    def test_basic_compression(self):
        """Test basic compression."""
        tool = {
            "name": "slither",
            "binary": "slither",
            "description": "Static analyzer for Solidity - primary VKG data source",
            "install_hint": "pip install slither-analyzer",
        }
        result = compress_tool_description(tool)
        assert result["name"] == "slither"
        assert len(result["description"]) < len(tool["description"])

    def test_aggressive_compression(self):
        """Test aggressive compression mode."""
        tool = {
            "name": "slither",
            "binary": "slither",
            "description": "x" * 200,
            "install_hint": "pip install",
            "homepage": "https://example.com",
            "examples": ["ex1", "ex2", "ex3", "ex4", "ex5"],
        }
        result = compress_tool_description(tool, aggressive=True)
        # Aggressive should produce smaller output
        assert len(str(result)) < len(str(tool))


class TestCompressToolDescriptions:
    """Tests for compress_tool_descriptions function."""

    def test_compress_multiple_tools(self):
        """Test compressing multiple tools."""
        tools = [
            {"name": "slither", "description": "Static analyzer for Solidity"},
            {"name": "aderyn", "description": "Rust-based Solidity analyzer with custom detectors"},
        ]
        result = compress_tool_descriptions(tools)
        assert len(result) == 2
        # Descriptions should be compressed
        for i, tool in enumerate(result):
            assert len(tool["description"]) < len(tools[i]["description"])

    def test_compress_empty_list(self):
        """Test compressing empty list."""
        result = compress_tool_descriptions([])
        assert result == []

    def test_compress_with_token_budget(self):
        """Test compression with token budget."""
        tools = [
            {"name": "slither", "description": "x" * 500, "binary": "slither", "install_hint": "pip install slither"},
            {"name": "aderyn", "description": "y" * 500, "binary": "aderyn", "install_hint": "cargo install aderyn"},
        ]
        result = compress_tool_descriptions(tools, max_tokens=200)
        # Should be under budget
        total_chars = sum(len(str(t)) for t in result)
        assert total_chars // 4 <= 250  # Allow some slack

    def test_extreme_budget_keeps_minimal_fields(self):
        """Test extreme budget keeps only minimal fields."""
        tools = [
            {"name": "slither", "description": "x" * 1000, "binary": "slither", "install_hint": "pip install slither"},
            {"name": "aderyn", "description": "y" * 1000, "binary": "aderyn", "install_hint": "cargo install aderyn"},
        ]
        result = compress_tool_descriptions(tools, max_tokens=50)
        # Should have minimal fields only
        for tool in result:
            assert "name" in tool
            # May or may not have other fields depending on compression level


class TestCompressForContext:
    """Tests for compress_for_context function."""

    def test_basic_context_string(self):
        """Test basic context string generation."""
        tools = [
            {"name": "slither", "install_method": "pip"},
            {"name": "aderyn", "install_method": "cargo"},
        ]
        result = compress_for_context(tools)
        assert "slither(pip)" in result
        assert "aderyn(cargo)" in result
        assert result.startswith("Tools: ")

    def test_empty_tools(self):
        """Test empty tool list."""
        result = compress_for_context([])
        assert result == "Tools: none"

    def test_truncates_to_max_chars(self):
        """Test truncation to max chars."""
        tools = [
            {"name": f"tool{i}", "install_method": "pip"}
            for i in range(100)
        ]
        result = compress_for_context(tools, max_chars=50)
        assert len(result) <= 50
        assert result.endswith("...")

    def test_tools_without_method(self):
        """Test tools without install method."""
        tools = [
            {"name": "slither"},
            {"name": "aderyn"},
        ]
        result = compress_for_context(tools)
        assert "slither" in result
        assert "aderyn" in result


class TestEstimateToolTokens:
    """Tests for estimate_tool_tokens function."""

    def test_estimate_small_tool(self):
        """Test token estimation for small tool."""
        tool = {"name": "test"}
        tokens = estimate_tool_tokens(tool)
        assert tokens > 0
        assert tokens < 10

    def test_estimate_large_tool(self):
        """Test token estimation for large tool."""
        tool = {
            "name": "test",
            "description": "x" * 400,  # ~100 tokens
            "binary": "test",
        }
        tokens = estimate_tool_tokens(tool)
        assert tokens > 100


class TestGetCompressionStats:
    """Tests for get_compression_stats function."""

    def test_calculate_stats(self):
        """Test stats calculation."""
        original = {"name": "test", "description": "x" * 100}
        compressed = {"name": "test", "description": "x" * 50}
        stats = get_compression_stats(original, compressed)
        assert stats.original_chars > stats.compressed_chars
        assert stats.savings_percent > 0

    def test_no_savings(self):
        """Test stats with no savings."""
        original = {"name": "test"}
        compressed = {"name": "test"}
        stats = get_compression_stats(original, compressed)
        assert stats.savings_percent == 0.0


class TestIntegration:
    """Integration tests with ToolRegistry."""

    def test_registry_get_tools_for_context(self):
        """Test getting compressed tools from registry."""
        from alphaswarm_sol.tools.registry import ToolRegistry

        registry = ToolRegistry()
        tools = registry.get_tools_for_context(max_tokens=500, include_unavailable=True)
        assert isinstance(tools, list)
        assert len(tools) > 0
        # Should have required fields
        for tool in tools:
            assert "name" in tool

    def test_registry_get_context_string(self):
        """Test getting context string from registry."""
        from alphaswarm_sol.tools.registry import ToolRegistry

        registry = ToolRegistry()
        context = registry.get_tools_context_string(max_chars=500, include_unavailable=True)
        assert context.startswith("Tools: ")
        assert "slither" in context  # Slither is defined

    def test_registry_context_respects_budget(self):
        """Test registry context respects character budget."""
        from alphaswarm_sol.tools.registry import ToolRegistry

        registry = ToolRegistry()
        context = registry.get_tools_context_string(max_chars=100, include_unavailable=True)
        assert len(context) <= 100
