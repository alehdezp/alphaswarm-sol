"""Tests for Tool Result Cache with Pool Scoping.

Phase 7.1.3-04: Query & Tool Caching.

Tests cover:
- Basic cache hit/miss behavior
- TTL expiry
- Pool-scoped caching and invalidation
- Run-scoped caching and invalidation
- Cache statistics with pool info
"""

import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import List
from unittest import TestCase, main

from alphaswarm_sol.cache.tool_results import (
    CacheKey,
    CachedResult,
    ToolResultCache,
    create_cache,
)
from alphaswarm_sol.tools.config import ToolConfig
from alphaswarm_sol.tools.adapters.sarif import VKGFinding


def make_test_finding(rule_id: str = "test-rule") -> VKGFinding:
    """Create a test VKGFinding with all required fields."""
    return VKGFinding(
        source="slither",
        rule_id=rule_id,
        title="Test finding",
        description="Test finding description",
        severity="high",
        category="test",
        file="Contract.sol",
        line=1,
    )


def make_test_findings(count: int = 1) -> List[VKGFinding]:
    """Create a list of test findings."""
    return [make_test_finding(f"rule-{i}") for i in range(count)]


class TestCacheKeyWithPooling(TestCase):
    """Tests for CacheKey with pool/run scoping."""

    def test_basic_key_to_filename(self):
        """Test basic filename generation."""
        key = CacheKey(
            tool="slither",
            file_hash="abc123def456789",
            config_hash="cfg12345678",
        )
        filename = key.to_filename()
        self.assertEqual(filename, "slither_abc123def456_cfg12345.json")

    def test_key_with_pool_to_filename(self):
        """Test filename includes pool_id."""
        key = CacheKey(
            tool="slither",
            file_hash="abc123def456789",
            config_hash="cfg12345678",
            pool_id="pool-001",
        )
        filename = key.to_filename()
        self.assertIn("pool-001", filename)
        self.assertTrue(filename.endswith(".json"))

    def test_key_with_run_to_filename(self):
        """Test filename includes run_id."""
        key = CacheKey(
            tool="slither",
            file_hash="abc123def456789",
            config_hash="cfg12345678",
            pool_id="pool-001",
            run_id="run-abc",
        )
        filename = key.to_filename()
        self.assertIn("pool-001", filename)
        self.assertIn("run-abc", filename)

    def test_key_sanitizes_special_chars(self):
        """Test that special characters in pool/run are sanitized."""
        key = CacheKey(
            tool="slither",
            file_hash="abc123def456789",
            config_hash="cfg12345678",
            pool_id="pool/001\\test",
            run_id="run/123",
        )
        filename = key.to_filename()
        self.assertNotIn("/", filename)
        self.assertNotIn("\\", filename)

    def test_key_to_dict_includes_pool_run(self):
        """Test to_dict includes pool_id and run_id when set."""
        key = CacheKey(
            tool="slither",
            file_hash="abc123",
            config_hash="cfg123",
            pool_id="pool-001",
            run_id="run-001",
        )
        data = key.to_dict()
        self.assertEqual(data["pool_id"], "pool-001")
        self.assertEqual(data["run_id"], "run-001")

    def test_key_to_dict_omits_none_pool_run(self):
        """Test to_dict omits pool_id and run_id when None."""
        key = CacheKey(
            tool="slither",
            file_hash="abc123",
            config_hash="cfg123",
        )
        data = key.to_dict()
        self.assertNotIn("pool_id", data)
        self.assertNotIn("run_id", data)

    def test_key_from_dict_with_pool_run(self):
        """Test from_dict parses pool_id and run_id."""
        data = {
            "tool": "slither",
            "file_hash": "abc123",
            "config_hash": "cfg123",
            "pool_id": "pool-001",
            "run_id": "run-001",
        }
        key = CacheKey.from_dict(data)
        self.assertEqual(key.pool_id, "pool-001")
        self.assertEqual(key.run_id, "run-001")


class TestToolResultCachePoolScoping(TestCase):
    """Tests for pool-scoped caching."""

    def setUp(self):
        """Set up temporary cache directory."""
        self.temp_dir = tempfile.mkdtemp()
        self.cache_dir = Path(self.temp_dir)
        self.cache = ToolResultCache(self.cache_dir, ttl_hours=24)

        # Create a minimal project with a .sol file
        self.project_dir = self.cache_dir / "test_project"
        self.project_dir.mkdir()
        (self.project_dir / "Contract.sol").write_text("// SPDX-License-Identifier: MIT\n")

        # Simple tool config
        self.config = ToolConfig(tool="slither")

    def tearDown(self):
        """Clean up temporary directory."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_put_with_pool_id(self):
        """Test caching with pool_id."""
        findings = make_test_findings(1)

        result = self.cache.put(
            tool="slither",
            project_path=self.project_dir,
            config=self.config,
            findings=findings,
            exec_time=1.5,
            pool_id="pool-001",
        )

        self.assertTrue(result)

    def test_get_with_pool_id(self):
        """Test retrieving with matching pool_id."""
        findings = make_test_findings(1)

        self.cache.put(
            tool="slither",
            project_path=self.project_dir,
            config=self.config,
            findings=findings,
            exec_time=1.0,
            pool_id="pool-001",
        )

        # Should find with matching pool_id
        cached = self.cache.get(
            tool="slither",
            project_path=self.project_dir,
            config=self.config,
            pool_id="pool-001",
        )
        self.assertIsNotNone(cached)
        self.assertEqual(len(cached.findings), 1)

    def test_get_with_different_pool_id_misses(self):
        """Test that different pool_id results in cache miss."""
        findings = make_test_findings(1)

        self.cache.put(
            tool="slither",
            project_path=self.project_dir,
            config=self.config,
            findings=findings,
            exec_time=1.0,
            pool_id="pool-001",
        )

        # Should miss with different pool_id
        cached = self.cache.get(
            tool="slither",
            project_path=self.project_dir,
            config=self.config,
            pool_id="pool-002",
        )
        self.assertIsNone(cached)

    def test_invalidate_pool(self):
        """Test invalidating all entries for a pool."""
        findings = make_test_findings(1)

        # Create entries for two pools
        self.cache.put(
            tool="slither",
            project_path=self.project_dir,
            config=self.config,
            findings=findings,
            exec_time=1.0,
            pool_id="pool-A",
        )

        # Create a different project for pool-B
        project_b = self.cache_dir / "test_project_b"
        project_b.mkdir()
        (project_b / "Contract.sol").write_text("// Different\n")

        self.cache.put(
            tool="slither",
            project_path=project_b,
            config=self.config,
            findings=findings,
            exec_time=1.0,
            pool_id="pool-B",
        )

        # Invalidate pool-A
        removed = self.cache.invalidate_pool("pool-A")
        self.assertEqual(removed, 1)

        # pool-A entry should be gone
        cached_a = self.cache.get(
            tool="slither",
            project_path=self.project_dir,
            config=self.config,
            pool_id="pool-A",
        )
        self.assertIsNone(cached_a)

        # pool-B entry should remain
        cached_b = self.cache.get(
            tool="slither",
            project_path=project_b,
            config=self.config,
            pool_id="pool-B",
        )
        self.assertIsNotNone(cached_b)

    def test_invalidate_run(self):
        """Test invalidating entries for a run."""
        findings = make_test_findings(1)

        self.cache.put(
            tool="slither",
            project_path=self.project_dir,
            config=self.config,
            findings=findings,
            exec_time=1.0,
            pool_id="pool-A",
            run_id="run-001",
        )

        # Create entry with different run
        project_b = self.cache_dir / "test_project_b"
        project_b.mkdir()
        (project_b / "Contract.sol").write_text("// Different\n")

        self.cache.put(
            tool="slither",
            project_path=project_b,
            config=self.config,
            findings=findings,
            exec_time=1.0,
            pool_id="pool-A",
            run_id="run-002",
        )

        # Invalidate run-001
        removed = self.cache.invalidate_run("run-001", pool_id="pool-A")
        self.assertEqual(removed, 1)

        # run-001 entry should be gone
        cached_1 = self.cache.get(
            tool="slither",
            project_path=self.project_dir,
            config=self.config,
            pool_id="pool-A",
            run_id="run-001",
        )
        self.assertIsNone(cached_1)

        # run-002 entry should remain
        cached_2 = self.cache.get(
            tool="slither",
            project_path=project_b,
            config=self.config,
            pool_id="pool-A",
            run_id="run-002",
        )
        self.assertIsNotNone(cached_2)

    def test_list_pools(self):
        """Test listing pools with cached entries."""
        findings = make_test_findings(1)

        self.cache.put(
            tool="slither",
            project_path=self.project_dir,
            config=self.config,
            findings=findings,
            exec_time=1.0,
            pool_id="pool-A",
        )

        project_b = self.cache_dir / "test_project_b"
        project_b.mkdir()
        (project_b / "Contract.sol").write_text("// Different\n")

        self.cache.put(
            tool="slither",
            project_path=project_b,
            config=self.config,
            findings=findings,
            exec_time=1.0,
            pool_id="pool-B",
        )

        pools = self.cache.list_pools()
        self.assertEqual(sorted(pools), ["pool-A", "pool-B"])

    def test_stats_include_pool_info(self):
        """Test that stats include pool tracking."""
        findings = make_test_findings(1)

        self.cache.put(
            tool="slither",
            project_path=self.project_dir,
            config=self.config,
            findings=findings,
            exec_time=1.0,
            pool_id="pool-A",
        )

        stats = self.cache.get_cache_stats()
        self.assertIn("pools_tracked", stats)
        self.assertEqual(stats["pools_tracked"], 1)
        self.assertIn("tool_distribution", stats)
        self.assertEqual(stats["tool_distribution"].get("slither"), 1)


class TestToolResultCacheHitMiss(TestCase):
    """Tests for cache hit/miss behavior."""

    def setUp(self):
        """Set up temporary cache."""
        self.temp_dir = tempfile.mkdtemp()
        self.cache = ToolResultCache(Path(self.temp_dir), ttl_hours=24)

        self.project_dir = Path(self.temp_dir) / "project"
        self.project_dir.mkdir()
        (self.project_dir / "Contract.sol").write_text("// Test\n")

        self.config = ToolConfig(tool="slither")

    def tearDown(self):
        """Clean up."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_cache_hit(self):
        """Test cache hit increments stats."""
        findings = make_test_findings(1)

        self.cache.put("slither", self.project_dir, self.config, findings, 1.0)

        # First hit
        self.cache.get("slither", self.project_dir, self.config)
        # Second hit
        self.cache.get("slither", self.project_dir, self.config)

        stats = self.cache.get_cache_stats()
        self.assertEqual(stats["hits"], 2)

    def test_cache_miss(self):
        """Test cache miss increments stats."""
        # Try to get non-existent entry
        self.cache.get("slither", self.project_dir, self.config)
        self.cache.get("slither", self.project_dir, self.config)

        stats = self.cache.get_cache_stats()
        self.assertEqual(stats["misses"], 2)

    def test_hit_rate_percent(self):
        """Test hit rate calculation."""
        findings = make_test_findings(1)

        self.cache.put("slither", self.project_dir, self.config, findings, 1.0)

        # 3 hits
        self.cache.get("slither", self.project_dir, self.config)
        self.cache.get("slither", self.project_dir, self.config)
        self.cache.get("slither", self.project_dir, self.config)
        # 1 miss
        self.cache.get("aderyn", self.project_dir, self.config)

        stats = self.cache.get_cache_stats()
        self.assertEqual(stats["hit_rate_percent"], 75.0)


class TestCreateCacheHelper(TestCase):
    """Tests for create_cache helper function."""

    def test_create_cache_returns_tool_result_cache(self):
        """Test create_cache returns proper instance."""
        temp_dir = tempfile.mkdtemp()
        try:
            cache = create_cache(Path(temp_dir), ttl_hours=12)
            self.assertIsInstance(cache, ToolResultCache)
            self.assertEqual(cache.ttl_hours, 12)
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    main()
